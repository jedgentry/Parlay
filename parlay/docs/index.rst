
.. include:: src/overview.rst

Promenade Software, the company that created Parlay, specializes in developing
software for safety-critical industries, such as medical devices, aerospace, and
automotive.  Parlay was built to streamline development and testing of embedded
software.

What is Parlay?
---------------
Parlay is a development framework that provides:

  * a built-in browser-based user interface to poke and prod connected items
  * a drag and drop UI builder that lets make a custom screen of buttons, sliders, graphs and more.
  * pre-built components to connect to devices over serial, TCP/IP, ModBus, GPIB and more
  * dead-simple scripting framework to write testing and development scripts in Python


Parlay serves a web application that provides a poke & prod user interface to all
connected items.  Via the user interface, users can send commands to and view responses
from items, change item properties, and graph item datastreams.  This user interface
can be accessible over a network for development and testing, or served securely in
production for remote diagnostics and service.

At the heart of Parlay is the "broker", which provides publish/subscribe message
routing between items. Once items are connected to the broker, they are easily accessible from the user interface,
scripts, and any other item.


Documentation Contents
----------------------

.. toctree::
    :hidden:

    Overview <src/overview>
    src/examples/led_example
    src/getting_started/getting_started
    UI: Explore Items <src/ui/user_interface>
    Scripts: Automate Control <src/scripts>
    Architecture: Under the Hood <src/architecture/overview_architecture>
    Protocols: Integrate existing devices <src/protocols/protocols>
    src/tutorials/tutorials
    src/apidoc/apidoc
    Specifications <src/specs/specs>
