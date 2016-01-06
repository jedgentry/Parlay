"""
Parlay
**********************************

Parlay is a versatile development system that can help speed embedded application development and integration in the
IoT age. Parlay acts as communication platform, test utility, and control interface for embedded devices.

Overview
----------------------------------

Broker
=================================

The heart of Parlay is the Broker. The Broker can open protocols, discover endpoints and route messages to the correct
subscriber. Endpoints publish messages to the Broker. Other endpoints subscribe to message that match a certain format.
The Broker will send all published message get to all subscribers. The broker, currently, does not have any delivery
 guarantees or message time-delay catch up ability.

Protocols
=================================
Protocols connect Endpoints to the broker. Protocols are also responsible for running discovery and reporting discover
 to the broker, so that the Ui and other endpoints can know what is currently connected to the system.

 For more information on Protocols and messages, see the documentation in the protocol package.

Messages
=================================
Endpoints send Messages over Protocols. Messages are key value pairs, commonly represented over JSON that only have
2 requirements.

* Each message must have a 'topics' key and a 'contents' key at the top level. Key, value pairs under the
'Topics' key can be subscribed to, but nothing 'contents' can be subscribed to.
* Under 'topics' there must be a key 'type' and a string value. This tells the Broker and other Endpoints
 the type of the message and how it should be interpreted.

 Basic example of a message:  {'topics': {'type': 'some_type'}, 'contents': [1,2,3,4,5,6,7] }

Endpoints
=================================
Endpoints are generic 'objects' that are discoverable in the system. The only hard requirement for all Endpoints is that
 they have a name and type. Both name and type are strings, but the type string is hierarchical with an 'is-a' object
 oriented relationship. For example an Endpoint with the type string 'SW_Dev/DirectMessage/Endpoint' would be an
  endpoint of type Sw_dev that inherits from DirectMessage that inherits from Endpoint. Each level in the hierarchy
  defines more about that Endpoint, its requirements and how to style the endpoint in the UI.

Interfaces
=================================
Endpoints can also implement Interfaces. Interfaces are generic I/O protocols that have pre-built widgets for users.
For example, if an Endpoint implements the 'MOTOR' interface, then a user can use a motor widget on the UI to control
speed and direction intuitively, and hook that Endpoint with other Endpoints that require a 'MOTOR'. If the Endpoint
implements the 'DATASTREAM' interface, then the user can graph an output stream from that Endpoint.

"""
from server.broker import Broker

# Broker public API
Modes = Broker.Modes
start = Broker.start
def open_protocol(protocol_name, **kwargs):
    """
    Open a protocol right when the Broker initializes
    """
    broker = Broker.get_instance()
    broker.call_on_start(lambda: broker.open_protocol(protocol_name, **kwargs))

# Endpoint Public API
from endpoints.parlay_standard import ParlayCommandEndpoint, parlay_property, parlay_command, parlay_datastream
from protocols.local_endpoint import local_endpoint

# Script Public API
from scripts.parlay_script import ParlayScript