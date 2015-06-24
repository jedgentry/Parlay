"""
.. py:module:: parlay.protocols

***********************************
H1 -- Protocols
***********************************

Broker messages are just key-value pairs stored in python dictionaries. The only general requirment for a message is that
it must have a 'topics' key and a 'contents' key at the root of the dictionary. Topics can be *subscribed* to and contents
can not. There are no other hard requirements for messages.

Each messaging protocol can define its own requirements for the types of messages it is expecting. Typically a messases
'type' is stored in msg['topics']['type']. This message type field is optional but **strongly** recommended.
For example broker messages have a type of 'broker'. So a broker message looks like::
    {'topics': {'type': 'broker', 'request':'get_protocols'}, 'contents': {} }


See a protocol's documentation for any specifics about the format of its message type.


Common protocol message definitions
########################################


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

"""