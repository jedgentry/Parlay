===============================
Overview of Parlay Architecture
===============================


Introduction
------------

Parlay is a development ecosystem that enables:

-  Communication with devices and between coding environments
-  Instant “poke and prod” UI for engineers and scientists
-  Simulation of hardware
-  Scripting and unit testing

For example, if you are developing a complex medical device:

-  Application engineers can develop the user interface without waiting
   hardware by completely simulating the hardware responses
-  Embedded engineers can easily test hardware to learn how to
   communicate and work with it
-  Scientists can use the built-in User Interface to experiment with the
   device on multiple levels
-  Anyone (software developers, electrical and mechanical engineers, or
   scientists) can write and modify scripts to automate testing and
   increase the speed and power of their experimentation
-  Code written during the early prototyping stages doesn't have to be
   thrown away. Parlay is intended to be part of your production system.
-  Service technicians can be given a separate user interface for
   service, with powerful diagnostic capabilities
-  Parlay supports secure remote access, so you can run your service
   diagnostics from anywhere in the world.

Two ways of running Parlay
--------------------------

Parlay is cross-platform, and it is designed to run either on a PC or an
embedded system.

PC Diagnostic Mode
~~~~~~~~~~~~~~~~~~

Parlay can be installed on your PC to aid development. This is how you
would most likely work with Parlay during the early stages of product development.

.. image:: images/parlay_pc_mode.png
    :alt: Parlay PC Mode diagram

Device Embedded Mode
~~~~~~~~~~~~~~~~~~~~

Parlay can also be installed on any embedded device that runs an
operating system that supports Python, such as any version of Linux or
Windows. Parlay is designed to be incorporated as a key component of
your product. It provides powerful service and diagnostic capabilities
to production devices.

.. image:: images/parlay_embed_mode.png
    :alt: Parlay Device Embedded Mode diagram

Architecture
------------

The core of Parlay is the broker, which routes messages between items in
a publish/subscribe scheme. Any item that connects to Parlay can
subscribe to receive messages that contain certain fields, and send
messages that other items can subscribe to. For many common use cases,
you will not need to interact with Parlay's messaging infrastructure
directly. There are many pre-built components that handle the details of
sending and receiving messages for you.

.. image:: images/parlay_architecture.png
   :alt: Parlay Architecture
