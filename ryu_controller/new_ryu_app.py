from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.controller.controller import Datapath
from ryu.ofproto import ofproto_v1_0

from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp

from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import Response
from ryu.app.wsgi import WSGIApplication
from ryu.app.wsgi import Request

from routes import Mapper

import logging
import typing
import json

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def route_handler(method):
    def wrapper(self, req: Request, *args, **kwargs):
        if req.method == 'POST':
            if req.headers.get('ContentType') != 'application/json' or not req.body:
                message = {'status': 'E_INV_CONTENT'}
                return Response(content_type='application/json', body=json.dumps(message), status=400)
        
        try:
            (body, status) = method(self, req, *args, **kwargs)
            return Response(content_type='application/json', body=json.dumps(body), status=status)
        except json.JSONDecodeError:
            return Response(
                content_type='application/json', body=json.dumps({'status': 'E_INV_BODY'}), 
                status=400
            )
        except:
            return Response(
                content_type='application/json', body=json.dumps({'status': 'E_INTERNAL_ERROR'}), 
                status=500
            )
    return wrapper

class RestController(ControllerBase):
    def __init__(self, req, link, data: typing.Dict, **config):
        super(RestController, self).__init__(req, link, data, **config)

    @route_handler
    def heartbeat(self, req, **_kwargs):
        return {'status': 'E_OK'}, 200
    
    @route_handler
    def set_server_address(self, req: Request, **_kwargs):
        payload: typing.Dict = json.loads(req.body.decode())

        if type(payload) != type({}):
            return {'status': 'E_INV_BODY'}, 400
        
        if payload.get('ip_address') == None:
            return {'status': 'E_MISSING_IP'}, 400
        
        self.data['server_ip'] = str(payload['ip_address'])

        logger.info('Set server address: ' + self.data['server_ip'])
        return {'status': 'E_OK'}, 200
    
    @route_handler
    def set_nat_address(self, req: Request, **_kwargs):
        payload: typing.Dict = json.loads(req.body.decode())

        if type(payload) != type({}):
            return {'status': 'E_INV_BODY'}, 400
        
        if payload.get('ip_address') == None:
            return {'status': 'E_MISSING_IP'}, 400
        
        self.data['nat_ip'] = str(payload['ip_address'])
        
        logger.info('Set nat address: '  + self.data['nat_ip'])
        return {'status': 'E_OK'}, 200

class CustomSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    _CONTEXTS = {
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(CustomSwitch, self).__init__(*args, **kwargs)
        self.data: typing.Dict[str, str] = {}
        self.mac_to_port: typing.Dict[typing.Any, typing.Dict[str, typing.Any]] = {}
        self.flow_table: typing.Dict[typing.Any, typing.Dict[str, typing.Any]] = {}
        self.last_cookie: int = 1
        wsgi: WSGIApplication = kwargs['wsgi']
        mapper: Mapper = wsgi.mapper

        wsgi.registory['RestController'] = self.data

        server_path = '/set_server_address'
        nat_path = '/set_nat_address'
        mapper.connect('/heartbeat', controller=RestController, action='heartbeat', conditions=dict(method=['GET']))

        mapper.connect(server_path, controller=RestController, action='set_server_address', conditions=dict(method=['POST']))
        mapper.connect(nat_path, controller=RestController, action='set_nat_address', conditions=dict(method=['POST']))

    def add_flow(self, switch_dp: Datapath, match_rule, actions, priority=32768, cookie=0, timeout=0):
        ofproto_module = switch_dp.ofproto
        parser_module = switch_dp.ofproto_parser
        flow_mod = parser_module.OFPFlowMod(
            datapath=switch_dp, match=match_rule, priority=priority,
            command=ofproto_module.OFPFC_ADD, actions=actions,
            cookie=cookie, hard_timeout=timeout
        )
        switch_dp.send_msg(flow_mod)
        return
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_handshake(self, ev: ofp_event.EventOFPMsgBase):
        dp: Datapath = ev.msg.datapath
        ofproto_module = dp.ofproto
        parser_module = dp.ofproto_parser
        #Match any packet
        match_rule = parser_module.OFPMatch()
        #Action send to controller
        actions = [parser_module.OFPActionOutput(ofproto_module.OFPP_CONTROLLER)]
        logger.info('Setting flow for fallback')
        #Add flow
        self.add_flow(dp, match_rule, actions, priority=0, cookie=0)
        return
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev: ofp_event.EventOFPMsgBase):
        if self.data.get('server_ip') == None or self.data.get('nat_ip') == None:
            logger.info('PANIK!')
            return
        
        msg = ev.msg
        dp: Datapath = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        switch_in_port = msg.in_port

        #Decode packet to extract ethernet
        #frame 
        _packet = packet.Packet(msg.data)
        _eth: ethernet.ethernet = _packet.get_protocols(ethernet.ethernet)[0]

        if _eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        if not dp.id in self.mac_to_port:
            self.mac_to_port[dp.id] = {}
            self.flow_table[dp.id] = {}

        self.mac_to_port[dp.id][_eth.src] = switch_in_port
        
        arp_protocol_list = _packet.get_protocols(arp.arp)

        if len(arp_protocol_list) > 0 :
            _arp: arp.arp = arp_protocol_list[0]
            server_check: bool = _arp.src_ip != self.data['server_ip'] and _arp.dst_ip != self.data['server_ip']
            nat_check: bool = _arp.src_ip != self.data['nat_ip'] and _arp.dst_ip != self.data['nat_ip']
            if server_check and nat_check:
                logger.info(f'Dropping ARP packet from {_arp.src_ip} to {_arp.dst_ip}')
                return 
            actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            out = ofp_parser.OFPPacketOut(
                datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
                actions=actions, data=msg.data)
            dp.send_msg(out)
            return

        ipv4_protocol_list = _packet.get_protocols(ipv4.ipv4)

        if len(ipv4_protocol_list) == 0:
            return

        _ipv4: ipv4.ipv4 = ipv4_protocol_list[0]
        
        logger.info(f'Packet from {_ipv4.src} to {_ipv4.dst}')

        server_check: bool = _ipv4.src != self.data['server_ip'] and _ipv4.dst != self.data['server_ip']
        nat_check: bool = _ipv4.src != self.data['nat_ip'] and _ipv4.dst != self.data['nat_ip']

        if server_check and nat_check:
            logger.info(f'Dropping IPv4 packet from {_ipv4.src} to {_ipv4.dst}')
            return
        
        if self.mac_to_port[dp.id].get(_eth.dst) == None:
            actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
            out = ofp_parser.OFPPacketOut(
                datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
                actions=actions, data=msg.data)
            dp.send_msg(out)
            return 
        
        actions = [ofp_parser.OFPActionOutput(self.mac_to_port[dp.id][_eth.dst])]
        
        if not f'{switch_in_port}-{_eth.src}-{_eth.dst}' in self.flow_table[dp.id].keys():
            #logger.info(f'Controller received packet even though flow rule already exists')
            logger.info(f'Add flow {switch_in_port} {_eth.src} -> {_eth.dst}')
            match_rule = ofp_parser.OFPMatch(in_port=switch_in_port, dl_dst=_eth.dst, dl_src=_eth.src)
            self.add_flow(dp, match_rule, actions, priority=1, cookie=self.last_cookie, timeout=10)
            self.flow_table[dp.id][f'{switch_in_port}-{_eth.src}-{_eth.dst}'] = self.last_cookie
            self.last_cookie += 1

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data

        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        dp.send_msg(out)
        return
    
    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed(self, ev: ofp_event.EventOFPMsgBase):
        msg = ev.msg
        dp: Datapath = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        _match = msg.match

        #in_port=switch_in_port, dl_dst=_eth.dst, dl_src=_eth.src
        if not f'{_match.in_port}-{_match.dl_src}-{_match.dl_dst}' in self.flow_table[dp.id].keys():
            return
        
        if msg.reason == ofp.OFPRR_DELETE:
            logger.info(f'Removing delete flow {_match.in_port}-{_match.dl_src}-{_match.dl_dst} from table')
            del self.flow_table[dp.id][f'{_match.in_port}-{_match.dl_src}-{_match.dl_dst}']
            return 
        
        in_port = _match.in_port
        mac_src = _match.dl_src
        mac_dst = _match.dl_dst

        logger.info(f'Reinserting deleted flow {_match.in_port}-{_match.dl_src}-{_match.dl_dst}')

        actions = [ofp_parser.OFPActionOutput(self.mac_to_port[dp.id][mac_dst])]
        match_rule = ofp_parser.OFPMatch(in_port=in_port, dl_dst=mac_dst, dl_src=mac_src)
        self.add_flow(dp, match_rule, actions, priority=1, cookie=self.last_cookie)
        self.flow_table[dp.id][f'{_match.in_port}-{_match.dl_src}-{_match.dl_dst}'] = self.last_cookie
        self.last_cookie += 1

        return