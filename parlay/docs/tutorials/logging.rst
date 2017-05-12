=======
Logging
=======

Parlay uses the standard python logging library to log messages, warnings and errors. All parlay JSON messages are logged at the
DEBUG level. Warnings and Errors are logged at their respective levels.

Parlay uses the recommended logging schema where the package name of the module that is logging (e.g. parlay.server.broker). That means
that if you want to log to a file, email, udp, etc you can add your handler to the "parlay" logger, or the root logger

Below is a simple example of how to attach a custom handler to the root logger that will cycle files every hour.
See the `python logging documentation
<https://docs.python.org/2/library/logging.html>`_ for more information on attaching handlers, filtering messages and logging.


.. code:: python

        from parlay import start, local_item, parlay_command, ParlayCommandItem

        @local_item(auto_connect=True)
        class CheerfulPerson(ParlayCommandItem):

            @parlay_command()
            def say_hello(self):
                return "Hello World!"

        if __name__ == "__main__":
            # import the standard logger library and a Timed Rotating logger handler
            import logging
            from logging.handlers import TimedRotatingFileHandler
            # get the ROOT logger for the entire process
            logger = logging.getLogger()
            # add the file handler to the root logger. Now any logged messages will be logged to files every hour (max 10)
            logger.addHandler(TimedRotatingFileHandler("LOG.txt", when="h", backupCount=10))
            # this function call starts Parlay, and does not return
            start()


The parlay logger defaults to logging.DEBUG .
To change the default log level of the parlay logger you can pass log_level to start()

.. code:: python

    start(log_level=logging.WARN)