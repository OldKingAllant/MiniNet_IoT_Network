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

import logging
import typing

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class CustomSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(CustomSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.flow_table: typing.Dict[typing.Any, typing.List[str]] = {}


    def add_flow(self, switch_dp: Datapath, match_rule, actions, priority=32768):
        ofproto_module = switch_dp.ofproto
        parser_module = switch_dp.ofproto_parser
        flow_mod = parser_module.OFPFlowMod(
            datapath=switch_dp, match=match_rule, priority=priority,
            command=ofproto_module.OFPFC_ADD, actions=actions
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
        self.add_flow(dp, match_rule, actions, priority=0)
        return

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp: Datapath = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        switch_in_port = msg.in_port

        #Decode packet to extract ethernet
        #frame 
        _packet = packet.Packet(msg.data)
        _eth = _packet.get_protocols(ethernet.ethernet)[0]

        if _eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        mac_dst = _eth.dst
        mac_src = _eth.src
        datapath_id = dp.id

        if self.mac_to_port.get(datapath_id) == None:
            self.mac_to_port[datapath_id] = {}
            self.flow_table[datapath_id] = []

        #Save source mac -> port
        self.mac_to_port[datapath_id][mac_src] = switch_in_port

        #Check if current destination was already saved in table
        #else do flood
        if self.mac_to_port[datapath_id].get(mac_dst) != None:
            out_cmd = self.mac_to_port[datapath_id][mac_dst]
        else:
            out_cmd = ofp.OFPP_FLOOD

        actions = [ofp_parser.OFPActionOutput(out_cmd)]

        #We already have the port that we need
        #to reach the mac address
        if out_cmd != ofp.OFPP_FLOOD and not f'{switch_in_port}-{mac_src}-{mac_dst}' in self.flow_table[datapath_id]:
            #Add a flow rule on the switch to avoid forwarding the packet
            #to the controller
            logger.info(f'Add flow {switch_in_port} {mac_src} -> {mac_dst}')
            match_rule = ofp_parser.OFPMatch(in_port=switch_in_port, dl_dst=mac_dst, dl_src=mac_src)
            self.add_flow(dp, match_rule, actions, priority=1)
            self.flow_table[datapath_id].append(f'{switch_in_port}-{mac_src}-{mac_dst}')

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data

        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        dp.send_msg(out)