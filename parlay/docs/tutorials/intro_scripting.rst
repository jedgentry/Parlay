=========================
Introduction to Scripting
=========================

Parlay scripts are extremely simple. By import a few functions from
parlay, you can repeatably and automatically control any item that is
connected to Parlay.

Scripts connect to Parlay
-------------------------

An important thing to understand about Parlay scripts is that they run
separately from the Parlay system. To run a script that controls items
that are connected to Parlay, *first run Parlay*, in the same way as the
`Hello World <hello_world>`__ tutorial. Then, in a separate command line
window, run your script. The script will automatically connect to the
Parlay broker over a websocket connection. It can then send messages to
and receive messages from other items that are connected to the Parlay
broker.

Basic Script to control Hello World item
----------------------------------------

Let's start with a very simple script, that will send a command to, and
read the response from, the "CheerfulPerson" item that we created in the
`Hello World <hello_world>`__ tutorial.

.. code:: python

    # simple_script.py

    from parlay.utils import setup, discover, get_item_by_name

    setup()  # required at the beginning of every script

    print "Discovering..."
    discover()  # required for future calls to 'get_item_by_name' to succeed
    print "Discovery Complete!"

    # cheeful_person is now the object representing the "CheerfulPerson" item connected to Parlay
    cheerful_person = get_item_by_name("CheerfulPerson")

    # send a command to cheerful_person just by calling the function corresponding to the command
    # response is the data returned by the command function in the item
    response = cheerful_person.say_hello()

    print response

First, run the `Hello World <Hello-World>`__ example, and *leave it
running*. You can close the browser user interface window if you wish
(it doesn't matter, because the Parlay server is still running in the
command line window).

Then, run this script in a separate command line from the hello world
example, and you should see the following output:

.. code:: bash

    c:\> python simple_script.py

     Discovering...
     Running discovery...
     Discovery Complete!
     Hello World!

Elements of a script
--------------------

These are the basic functions you can call in a script. To use any of
them, import them from parlay.utils, as seen in the simple example
above.

``setup()`` MUST be called at the beginning of every script.

``discover()`` is almost always required, since it will allow future
calls to ``get_item_by_name`` to succeed.

``get_item_by_name("NAME HERE")`` returns an object that represents an
item that is connected to the Parlay server. This will fail if the item
is not connected.

During discovery, any connected items will also report what commands
they support. In the case of `Hello World <Hello-World>`__, the
``CheerfulPerson`` item supports the ``say_hello()`` command. In the
script, all you have to do is call the function ``say_hello()``. Behind
the scenes, this will send a command to the item, and wait for the
response to come back. This is known as a *blocking* call. The script
will pause at this line until the item responds to the command. This is
easy to understand for beginners, and is a very common use case for
scripts.

Serial vs Parallel commands
---------------------------

Scripts are run in a separate process than the Parlay broker. All the
function calls in scripts can block without disturbing the Parlay
system. Command functions, like ``say_hello()`` that we called above,
have been designed as blocking function calls. The script will pause at
that function call until the item returns a response to the command. In
our simple Hello World example, the response comes very quickly.
However, Parlay is designed to work well with items that take a long
time to complete their commands.

Suppose you are building an embedded device with several motors. Each of
the motors might be represented as an item in Parlay, and you want to be
able to move two motors at the same time. You don't want to have to send
a "move" command to one motor and wait for it to be complete before
sending a "move" command to a second motor.

The ``send_parlay_command`` function gives you a way to do that.

Send a command now, wait for response later
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Below is a modification to the above example that uses
``send_parlay_command``, which returns a handle to the command. You can
use that handle later to wait for the response to the command.

.. code:: python

    cheerful_person = get_item_by_name("CheerfulPerson")
    command_handle = cheerful_person.send_parlay_command("say_hello")
    # other code can go here, which will execute without waiting for the response to "say_hello"
    response = command_handle.wait_for_complete()

Example with serial and parallel commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To demonstrate, let's run a more complicated example, with two items
that have slooooooooowwwww commands, and a script that exercises those
commands both serially and in parallel.

.. code:: python

    # items_with_slow_commands.py

    from parlay import start, local_item, ParlayCommandItem, parlay_command
    from parlay.utils import sleep


    @local_item(auto_connect=True)
    class Item1(ParlayCommandItem):

        @parlay_command()
        def slow_command_1(self):
            sleep(5)
            return "Command 1 Completed!"


    @local_item(auto_connect=True)
    class Item2(ParlayCommandItem):

        @parlay_command()
        def slow_command_2(self):
            sleep(5)
            return "Command 2 Completed!"


    if __name__ == "__main__":
        start(open_browser=False)  # you can avoid launching your web browser

Run the previous file on the command line to start Parlay:

.. code:: bash

    c:\> python items_with_slow_commands.py

In a separate command line, launch the following script:

.. code:: python

    # serial_vs_parallel_script.py

    from parlay.utils import setup, discover, get_item_by_name

    setup()
    discover()

    item1 = get_item_by_name("Item1")
    item2 = get_item_by_name("Item2")

    print "\nSending blocking commands"

    print "  Slow Command 1..."
    response1 = item1.slow_command_1()
    print response1

    print "  Slow Command 2..."
    response2 = item2.slow_command_2()
    print response2

    print "\nSending parallel commands"

    print "  Slow Command 1..."
    cmd1 = item1.send_parlay_command("slow_command_1")
    print "  Slow Command 2..."
    cmd2 = item2.send_parlay_command("slow_command_2")

    print "  Waiting for responses..."
    response1 = cmd1.wait_for_complete()["CONTENTS"]["RESULT"]
    response2 = cmd2.wait_for_complete()["CONTENTS"]["RESULT"]

    print response1
    print response2

.. code:: bash

    c:\> python serial_vs_parallel_script.py
    Connecting to localhost : 8085
    Running discovery...

    Sending blocking commands
      Slow Command 1...            <--- this takes 5 seconds
    Command 1 Completed!
      Slow Command 2...            <--- this takes 5 seconds
    Command 2 Completed!

    Sending parallel commands
      Slow Command 1...
      Slow Command 2...
      Waiting for responses...     <--- this takes 5 seconds
    Command 1 Completed!
    Command 2 Completed!

As expected, running the two commands serially takes about 10 seconds,
while running them in parallel takes only 5 seconds.

You can mix and match serial and parallel commands to any level of
complexity, which enables very powerful scripting capabilities.
