"""
Define a base class for creating a client script
"""
from bonobo._bonobo import Listener
from twisted.internet import threads, reactor, defer
from twisted.python.failure import Failure
import json
import sys
import traceback
from parlay.items.base import INPUT_TYPES, MSG_STATUS, MSG_TYPES, TX_TYPES
from parlay.protocols.utils import message_id_generator
import traceback
from parlay.items.threaded_item import ThreadedItem, ITEM_PROXIES, ListenerStatus
from parlay.items.parlay_standard import ParlayStandardItem


DEFAULT_ENGINE_WEBSOCKET_PORT = 8085


class ParlayScript(ThreadedItem):

    def __init__(self, item_id=None, name=None, _reactor=None):
        if item_id is None:
            item_id = self.__class__.__name__ + ".py"
        if name is None:
            name = self.__class__.__name__ + ".py"

        # default to default reactor
        _reactor = reactor if _reactor is None else _reactor
        # default script name and id to the name of this class
        ThreadedItem.__init__(self, item_id, name, _reactor)
        

    def on_message(self, msg):
        self._runListeners(msg)

    def subscribe(self, _fn=None, **topics):
        """
        Subscribe to messages the topics in **kwargs
        """
        self.publish({"TOPICS": {'type': 'subscribe'}, "CONTENTS": {'TOPICS': topics}})
        if _fn is not None:
            def listener(msg):
                topics = msg["TOPICS"]
                if all(k in topics and v == topics[k] for k, v in topics):
                    _fn(msg)
                return ListenerStatus.KEEP_LISTENER

            self.add_listener(listener)

    def publish(self, msg, callback):
        self.sendMessage(json.dumps(msg))

    def kill(self):
        """ Kill the current script """
        self.cleanup()

    def cleanup(self, *args):
        """
        Cleanup after running the script
        :param args:
        :return:
        """

        def internal_cleanup():
            self.transport.loseConnection()
            # should we stop the reactor on close?
            if self.__class__.stop_reactor_on_close:
                reactor.stop()

        self.sendClose()
        reactor.callLater(1, internal_cleanup)

    def _start_script(self):
        """ Init and run the script """
        # run the script and run cleanup after.
        defer = self.reactor.maybeDeferToThread(self._in_thread_run_script)
        defer.addBoth(self.cleanup)

    def _in_thread_run_script(self):
        """ Run the script. """
        try:
            self.run_script()

        except Exception as e:
            # handle any exception thrown
            exc_type,exc_value,exc_traceback = sys.exc_info()
            print "Exception Error:  ",  exc_value
            print e

            # print traceback, excluding this file
            traceback.print_tb(exc_traceback)
            # exc_strings = traceback.format_list(traceback.extract_tb(exc_traceback))
            # exc_strings = [s for s in exc_strings if s.find("parlay_script.py")< 0 ]
            # for s in exc_strings:
            #     print s

    def shutdown_broker(self):
        self.send_parlay_message({"TOPICS": {"type": "broker", 'request': 'shutdown'}, "CONTENTS": {}})

    def run_script(self):
        """
        This should be overridden by the script class
        """
        raise NotImplementedError()


def start_script(script_class, engine_ip='localhost', engine_port=DEFAULT_ENGINE_WEBSOCKET_PORT,
                 stop_reactor_on_close=None, skip_checks=False):
    """
    Construct a new script from the script class and start it

    :param script_class : The ParlayScript class to run (Must be subclass of ParlayScript)
    :param engine_ip : The ip of the broker that the script will be running on
    :param engine_port : the port of the broker that the script will be running on
    :param stop_reactor_on_close: Boolean regarding whether ot not to stop the reactor when the script closes
    (Defaults to False if the reactor is running, True if the reactor is not currently running)
    :param skip_checks : if True will not do sanity checks on script (CAREFUL: BETTER KNOW WHAT YOU ARE DOING!)
    """
    if not skip_checks:
        if not issubclass(script_class, ParlayScript):
            raise TypeError("start_script called with: "+str(script_class)+" \n" +
                            "Can only call start_script on an instance of a subclass of ParlayScript")

    # et whether to stop the reactor or not (default to the opposite of reactor running)
    script_class.stop_reactor_on_close = stop_reactor_on_close if stop_reactor_on_close is not None else not reactor.running

    # connect it up
    factory = WebSocketClientFactory("ws://" + engine_ip + ":" + str(engine_port))
    factory.protocol = script_class
    reactor.connectTCP(engine_ip, engine_port, factory)

    if not reactor.running:
        reactor.run()
