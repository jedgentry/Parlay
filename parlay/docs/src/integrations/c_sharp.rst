=========
C# (.NET)
=========


Defining Parlay Items with Properties and Commands
--------------------------------------------------

.. code:: c#

    using Parlay.NET

    public class CheerfulPerson
    {
        ParlayBaseAdapter m_adapter;
        ParlayItem<CheerfulPerson> m_item;

        ParlayProperty first_name("Sarah");

        public CheerfulPerson(ParlayBaseAdapter adapter, object item_id, string item_name)
        {
            m_adapter = adapter;
            m_item = new ParlayItem<CheerfulPerson>(adapter, this, item_name, item_id);
        }

        [ParlayCommand]
        public int sayHello(string name)
        {
            string message = sprintf("Hello %s, I'm %s!", name, this.first_name);
            return message;
        }

    }


Instantiate and connect an item to the Parlay Broker
----------------------------------------------------

.. code:: c#

    // The Parlay Broker maintains a websocket server listening for incoming websocket connections
    //   We need to know the IP address and port that the Parlay Broker is listening on

    string PARLAY_BROKER_URI = "localhost";
    string PARLAY_BROKER_PORT = 58085

    ParlayBaseAdapter adapter = new ParlayWebSocketAdapter(PARLAY_BROKER_URI, PARLAY_BROKER_PORT);

    CheerfulPerson person1 = new CheerfulPerson(adapter, "Cheerful Person 1", "Cheerful Person 1");
    CheerfulPerson person2 = new CheerfulPerson(adapter, "Cheerful Person 2", "Cheerful Person 2");

    adapter.connect();


Invoking commands and properties of other items
-----------------------------------------------

.. code:: c#

    using Parlay.NET

    await person1.setProperty<string>("Cheerful Person 2", "first_name", "Cindy");

    var args = new Dictionary<string, object>() {{ "name", "Janice"}};

    try
    {
        var result = await person1.sendCommand("Cheerful Person 2", "sayHello", args);
        Console.Write("Result: " + result);
    }
    catch (BadStatus e)
    {
        Console.Write("Error: " + e.Message);
    }

    person1