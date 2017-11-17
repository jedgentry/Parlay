===========
Hello World
===========

This is the simplest demonstration of the parlay system. In this
tutorial, we will create a Parlay `local_item` object, use the Parlay
User Interface to send it a command, and view the response.  The Item will
also demonstrate the use of Properties.


This code is available as part of the `Parlay Examples Repo <https://github.com/PromenadeSoftware/ParlayExamples>`_ on Github.


Create a ``local_item`` that says "Hello World!"
------------------------------------------------

Open a text editor and create a python script file named
"parlay\_hello.py" like so:

.. code:: python

    # parlay_hello.py

    import parlay

    @parlay.local_item()
    class CheerfulPerson(parlay.ParlayCommandItem):

        hello_message = parlay.ParlayProperty(default="Hello World!", val_type=str)
        first_name = parlay.ParlayProperty(default="Sarah", val_type=str)

        @parlay.parlay_command()
        def say_hello(self):
            return self.hello_message

        @parlay.parlay_command()
        def what_is_your_name(self):
            # properties can be used just like any variable of their value type
            return "My name is " + self.first_name + "!"


    if __name__ == "__main__":

        # parlay.start() will not exit, so we need to instantiate all local items before calling it
        CheerfulPerson("CheerfulPerson", "CheerfulPerson")
        parlay.start()

Save this script in any directory on your system.



Run the Hello World script
--------------------------

Use python to execute this script from the command line. For example, if
you saved the file to the C drive, you would open a command line, and
run the following command:

.. code:: bash

    c:\> python parlay_hello.py

Two things will now happen:

1) The parlay system will start running in the command line. Do not close 
   the command line window! 
2) Your default web browser will automatically open a new tab and go to 
   http://localhost:8080, where you will see the UI.

In the browser UI, you'll be able to see the "CheerfulPerson" item in the item dropdown box.
Open the item and try sending the "say_hello" command.  You'll see "Hello World!" as the result.

That's it! You've just created a Parlay Command Item, defined a command,
run Parlay, viewed the item's card in the UI, sent the item a command,
and viewed the response.



Parlay UI is a web application
------------------------------

This illustrates an important aspect of Parlay that can be confusing to
first-time users:

*Parlay runs a* **web server**, *and the built-in User Interface is a* **web application**.

Parlay and the web browser are two separate applications, that in this
simple example, are both running on your computer. This architecture
confers huge advantages in more advanced use cases, where you can run
Parlay on your embedded device. However, it is a little different than
the typical stand-alone desktop application that many users are
accustomed to.

-  If you really want to be done with Parlay, you must close the command
   line window AND the browser tab.

-  If you just close the web browser, Parlay is *still running*. To shut
   down Parlay, close the command line window where you started Parlay.
   If you did not mean to close the browser, you can re-open your web
   browser and navigate to http://localhost:8080, and Parlay will show
   the User Interface again.

-  If you close the command line window before the web browser, the
   browser will lose communication with Parlay and the User Interface
   will show a yellow warning message "Lost Connection with Broker".
   Run the python script again from a command line, click "Reconnect",
   and the UI will be ready again.
