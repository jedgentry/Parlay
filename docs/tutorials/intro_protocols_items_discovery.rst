===============================================
Introduction to Protocols, Items, and Discovery
===============================================

This article introduces the fundamental components of the Parlay
ecosystem: Items and Protocols.

Items
-----

In Parlay, an Item represents something physical (e.g. motor) or logical
(e.g. scheduler). Every item has a ‘Name’, ‘ID’ and ‘Type’. The ID
determines the Item’s identity, and must be unique among all items
connected to the Parlay broker. It can be a string or a number. The
broker uses the Item's ID to correctly route messages.

In the most general case, an Item is an object that can send and receive
messages that are routed by the Parlay broker. However, when creating
your own Items, you will inherit from Parlay Item classes that provide
more functionality out of the box.

Parlay provides three standard components for Items that are supported
by the built-in User Interface and by Parlay scripts:

* Commands: Take arguments and return a result or perform an action
* Properties: Can be "GET" and "SET" dynamically
* Datastreams: Read-only. Will send data updates at specified interval, and can be
  graphed in the User Interface

For more detailed instructions on creating your own logical items, see
`Local Items <local_items>`__.

Protocols
---------

A Protocol object is responsible for passing messages between one or
more Items and the Broker. It handles discovery for only the Items that
it is connecting to the Broker.

A Protocol object determines how to translate between a stream of bytes
(provided by a Transport) and Parlay messages. Transports represent the
physical layer (e.g: RS-232, CAN, TCP, etc.). By abstracting transports
to a stream of bytes, protocols can swap transports easily. For example,
something that runs over Serial could trivially be ported to TCP. Parlay
supports many common transport layers out-of-the-box, so it is unlikely
that you will need to write a custom Transport.

For more detailed instructions on creating your own protocols for
external devices, see `Custom Protocols <custom_protocols>`__.

Discovery
---------

One of the most powerful features of Parlay is discovery: finding out
what items are connected (and how they are connected) in real time,
rather than hard-coding them up-front. For example, you can write a
`script <intro_scripting>`__ that sends various commands to a
serial motor controller item with the ID of "Motor1". You can plug that
motor controller into any COM port on your PC, or even write a simulator
in python that simulates the communication with that motor controller.
As long as the item returns the ID "Motor1" during the discovery
operation, your script will work with zero changes.

See :doc:`case_study_serial_dc_motor_controller`
