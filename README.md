# Simple IoT network using mininet

This project has the objective of allowing the user to simulate an IoT network
with mininet. The user can define the topology in a text file
with the same format as 'test_topo.txt' and put the simulated sensors/actuators/controllers
in the respective directories. 

The application will setup the mininet instance and the various servers
on the created hosts, while creating a GUI application that would allow
interacting with the various devices

# How to run

First and foremost you need to have Mininet and Python 3.6+ installed on your machine, 
after that you will need to install Mosquitto, the open-source MQTT broker;
on Ubuntu:
````
apt install mosquitto
````

Then, install the required python dependencies:
````
pip3 install -r requirements.txt
````

Notice that, being a GUI application, if you are running on
a virtual machine without desktop, you must also have an X server
running, together with a client on your real computer. Make
sure to have the DISPLAY env. variable set!

Now clone the repository wherever you want and cd in the
root directory

Now you should have all the necessary dependencies to run the project!

1. Open 3 different shells
2. In the first, run mosquitto using the same configuration presented in the file 'mosquitto.conf'
3. In the second, start the ryu controller using 'ryu run ./ryu_controller/ryu_app.py'
4. In the last shell, you can run the application itself using 'sudo python3 app.py test_topo.txt remote'

If you have installed everything correctly, you should now see a Qt window

# Project structure 

- **actuators/**   Put here the scripts that behave as actuators
- **sensors/**     Put here the scripts that behave as sensors
- **controllers/** Put here the scripts that behave as controllers
- **ryu_controller/** Contains the ryu controller script
- **app_detail/**  Detail modules for the GUI app
- **server/**      Scripts for the flask servers
- **topo/**        Modules for loading topology from file
- **app.py/**      The main GUI application

# How does it work?

The network consists of three main host types:
- The 'room' host
- The IoT server
- The GUI application

## Room host

A 'room' host is declared as 'Host' in the topology file
and upon network creation, a HTTP server is started on this
host. The server waits for commands from the main 
server and adds/removes sensors and actuators when it
is told to do so. 

## IoT server

Runs an HTTP server that manages every devices
in the network, while also running all the IoT
controllers that are started by the user

## Main GUI app

Creates the Mininet network and opens the GUI, allowing
interactions with the IoT network. The application itself
is not run inside Mininet and for this reason a NAT
interface is implicitly added to the network 

# Iot devices and Controllers

## Sensors and Actuators

As we previously described, sensors and actuators
can be added to a 'room' host and are, in fact, python
scripts that are started by the host on a different
shell using popen. Each script must interface with
the rest of the network by using the already implemented
'actuator_class' and 'sensor_class', which automatically
create a connection to the MQTT broker and offer
an API for sending data and receiving commands.

## Controllers

Even controllers are simple scripts that must use 
the module 'controller_class'. Each controller can
receive data from the wanted sensors and send the
corresponding commands to some actuators. 

# Main server API

The API of the main IoT server offers the necessary
functionalities to start/stop sensors/actuators and
controllers and to receive data and status from each
device. Here is a quick summary of the endpoints:

- **POST/DELETE /devices**:               Add or remove new hosts to/from the list saved by the server. This should be done only at startup
- **POST /dev/<host_id>/sensors**:        Attach new sensor to the host
- **DELETE /dev/sensors/delete_all**:     Remove all sensors
- **GET /dev/sensors/get_all**:           Get list of all hosts and the sensors attached to each host
- **PUT /dev/<host_id>/sensor_stop**:     Prevent sensor from sending data
- **PUT /dev/<host_id>/sensor_start**:    Allow sensor data
- **GET /dev/<host_id>/sensor_status**:   Get sensor status
- **GET /dev/<host_id>/sensor_data**:     Get latest sensor data
- **POST /dev/<host_id>/actuators**:      Attach new actuator to the host
- **DELETE /dev/actuators/delete_all**:   Remove all actuators
- **GET /dev/actuators/get_all**:         Get list of all hosts and the actuators attached to each host
- **PUT /dev/<host_id>/actuator_stop**:   Stop actuator
- **PUT /dev/<host_id>/actuator_start**:  Start actuator
- **GET /dev/<host_id>/actuator_status**: Get actuator status
- **POST /controllers/add**:              Start new controller on the server
- **DELETE /controllers/remove**:         Stop controller
- **GET /controllers/get_all**:           Get all controllers on the server
- **DELETE /controllers/remove_all**:     Remove all controllers from server