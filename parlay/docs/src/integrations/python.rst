======
Python
======


Defining Parlay Items with Properties and Commands
--------------------------------------------------

.. code:: python

    from parlay import ParlayCommandItem, ParlayProperty, parlay_command, state

    # define an item
    class CheerfulPerson(ParlayCommandItem):

        # define a property
        first_name = ParlayProperty(default="Sarah", read_only=False)

        def __init__(item_id, item_name, adapter=None):
            ParlayCommandItem(item_id, item_name, adapter)

        # define a command
        @parlay_command
        def say_hello(name):
            message = "Hello {}, I'm {}!".format(name, self.first_name)
            return message



Instantiate and connect an item to the Parlay Broker
----------------------------------------------------

.. code:: python

    from parlay import start

    # instantiate an item
    CheerfulPerson(item_id="cheerful_person", item_name="Cheerful Person")

    # start the parlay broker
    #   any python item instantiated in the same python process as calling start()
    #   will automatically be connected to the broker
    start()


Invoking commands and properties of other items
-----------------------------------------------

.. code:: python

    from parlay.utils import get_item_by_id

    person = get_item_by_id("cheerful_person")

    # read a property
    remote_name = person.name

    # set a property
    person.name = "Cindy"

    # call a command and block until we receive the result
    result = person.say_hello("Janice")

    # call a command and get a handle that we can wait for later
    response = send_parlay_command("cheerful_person", "say_hello", args=["Janice"])

    # now wait for the response to come back to us
    response.wait_for_complete()

    result = response.result

