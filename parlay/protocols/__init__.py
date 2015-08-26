"""
.. py:module:: parlay.protocols

***********************************
Protocols
***********************************

Broker messages are just key-value pairs stored in python dictionaries. The only general requirement for a message is that
it must have a 'topics' key and a 'contents' key at the root of the dictionary. Topics can be *subscribed* to and contents
can not. There are no other hard requirements for messages.

Each messaging protocol can define its own requirements for the types of messages it is expecting. Typically a message
'type' is stored in msg['topics']['type']. This message type field is optional but **strongly** recommended.
For example broker messages have a type of 'broker'. So a broker message looks like::
    {'topics': {'type': 'broker', 'request':'get_protocols'}, 'contents': {} }


See a protocol's documentation for any specifics about the format of its message type.



Common protocol message definitions
########################################

Subscribe Messages
======================================
Message format:

* topics
    * type : subscribe
* contents
    * topics : {to_system : 100, }


Expected result:
* topics
    * type : subscribe_response
* contents
    * status : ok

Broker Messages
======================================

List protocols
-------------------

Message format:

* topics

    * type : broker
    * request : get_protocols

* contents


Example response:

* topics
    * status : ok
    * type : broker
    * response : get_protocols

* contents:

    * Serial

        * params : [port, baudrate]
        * defaults:

            * port : /dev/ttyUSB0
            * baudrate : 9600

    * TCP/IP

        * params : [ip, port]
        * defaults:

            * ip : localhost
            * port : 9001



Open Protocol
------------------------



Message format:

* topics

    * type : broker
    * request : open_protocol

* contents

    * protocol : Serial
    * params :
        * status : ok
        * port : /dev/ttyUSB1
        * baurdrate : 9600


Example response:

* topics

    * type : broker
    * response : open_protocol_response

* contents

    * status : ok
    * protocol : Serial
    * params :
        * name : Serial on /dev/ttyUSB0
        * status : ok
        * port : /dev/ttyUSB1
        * baurdrate : 9600

Example error Response

* topics

    * type : broker
    * response : open_protocol_response

* contents

    * status : No such port '/dev/ttyUSB1'
    * protocol : Serial
    * params :

        * port : /dev/ttyUSB1
        * baurdrate : 9600


List Open Protocols
-----------------------------

Message format:
* topics
    * type : broker
    * request : get_open_protocols

* contents:



Example Response:
* topics
    * type : broker
    * response : get_open_protocols_response


* contents:

    * open_protocols: [{'name': 'Serial on /dev/ttyUSB0', 'protocol_type': 'SSCOM_Serial'}, {'name': 'Websocket on 8085', 'protocol_type': 'Websocket'}]


Close a Protocol
---------------------------------
Message format:
* topics
    * type : broker
    * request : close_protocol

* contents:
    * protocol: 'Serial on /dev/ttyUSB0'



Example Response:
* topics
    * type : broker
    * response : close_response


* contents:
    * status : ok
    * open_protocols: ['Websocket on 8085']


Example Error Response:
* topics
    * type : broker
    * response : close_response


* contents:
    * status : 'No such protocol  \'Serial on /dev/ttyUSB0\' '
    * open_protocols: ['Websocket on 8085']



Discover attached endpoints
----------------------------------
In order to discover attached endpoints, send a 'discover' command to the broker.
The broker will respond back with a list of attached endpoints.

Message format:

* topics
    * type : broker
    * request : discover

* contents
    * force : true | false (optional. default=false)

The response will be a list of objects where each object will have a protocol name
and a list of children.  Each child will be an endpoint. Each endpoint will have a 'name'
and a 'type' field telling which endpoint type it is, and an optional 'children' field that will
be a list of other endpoint objects with the same requirements.  Depending on the 'type' of the
endpoint, there may be more fields in the object besides just 'type','name', (optional) 'interfaces', and (optionally)
'children'.

Example response:
* topics :
    * type: broker
    * response: discover_response

* contents : (list)

    [
        * type : protocol
        * name : Serial on /dev/ttyUSB0
        * protocol_type : SSCOM_Serial   ('protocol' type specific key/value)
        * message_types : [(0, "Command"),(1,"Command Response")]
        * status_types : [(0,"STATUS_OKAY"), ...]
        * children : (list)
            [
                * name : Motor System
                * type : SSCOM_SYSTEM/COMMAND_RESPONSE_SYSTEM/SYSTEM
                * children : (list)
                [
                    * name : Motor 1
                    * type : SSCOM/CommandResponse/Endpoint
                    * interface : [ Motor, Stepper Motor ]
                    * commands : { 5 : PREPARE, 105: MOVE_TO_POS, ...}   ('type' specific key/value)
                    ,
                    * name : Controller
                    * type : SSCOM/CommandResponse/Endpoint
                    * commands : { 5 : PREPARE, 105: START_RUN, ...}   ('type' specific key/value)
                    ,
                    *.......
                ]


            ]
    ]


Execute Python statement
----------------------------------

When in DEVELOPMENT mode, the broker allows remote protocols to execute arbitrary python statements. If in any other mode
the broker will REJECT the command and not execute the statement.

Message format:

* topics
    * type : broker
    * request : eval_statement

* contents
    * statement : the statement to evaluate as a string. This must be a single valid python statement (e.g.: 1+1 or [x for x in range(10)])


Example response:

* topics
    * type : broker
    * request : eval_statement_response

* contents
    * status : ok
    * result : 2  (the result of the statement 1+1)


Example Error Response:

* topics
    * type : broker
    * request : eval_statement_response

* contents
    * status : ERROR. Remote Evaluation not allowed unless in DEVELOPMENT MODE
    * result : ERROR. Remote Evaluation not allowed unless in DEVELOPMENT MODE

"""
