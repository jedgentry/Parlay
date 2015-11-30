"""
Define a base class for creating a client script
"""
from twisted.internet import threads, reactor, defer
from twisted.python.failure import Failure
from autobahn.twisted.websocket import  WebSocketClientProtocol, WebSocketClientFactory
import json
import sys
import traceback
from parlay.endpoints.base import INPUT_TYPES, MSG_STATUS, MSG_TYPES, TX_TYPES
from parlay.protocols.utils import message_id_generator
import traceback
from parlay.endpoints.threaded_endpoint import ThreadedEndpoint, ENDPOINT_PROXIES
from parlay.endpoints.parlay_standard import ParlayStandardEndpoint

DEFAULT_ENGINE_WEBSOCKET_PORT = 8085

class ParlayScript(ThreadedEndpoint, WebSocketClientProtocol):

    def __init__(self, endpoint_id=None, name=None):
        if endpoint_id is None:
            endpoint_id = self.__class__.__name__ + ".py"
        if name is None:
            name = self.__class__.__name__ + ".py"

        #default script name and id to the name of this class
        ThreadedEndpoint.__init__(self, endpoint_id, name)


    def _send_parlay_message(self, msg):
        self.sendMessage(json.dumps(msg))


    def onConnect(self, response):
        """
        Overriden from WebSocketClientProtocol. Called when Protocol is opened
        """
        WebSocketClientProtocol.onConnect(self, response)
        # schedule calling the script entry
        self.reactor.callLater(0, lambda: self._send_parlay_message({"TOPICS": {'type': 'subscribe'},
                                     "CONTENTS": {
                                         'TOPICS': {'TO': self.endpoint_id}
                                     }
        }))
        self.reactor.callLater(0, self._start_script)


    def onMessage(self, packet, isBinary):
        """
        We got a message.  See who wants to process it.
        """
        if isBinary:
            print "Scripts don't understand binary messages"
            return

        msg = json.loads(packet)
        # run it through the listeners for processing
        self._runListeners(msg)

    def kill(self):
        """
        kill the current script
        """
        self.cleanup()

    def cleanup(self, *args):
        """
        Cleanup after running the script
        :param args:
        :return:
        """

        def internal_cleanup():

            self.transport.loseConnection()
            #should we stop the reactor on close?
            if self.__class__.stop_reactor_on_close:
                reactor.stop()

        self.sendClose()
        reactor.callLater(1, internal_cleanup)


    def _start_script(self):
        """
        Init and run the script
        @param cleanup: Automatically clean up when we're done running
        """
        #run the script and run cleanup after.
        defer = threads.deferToThread(self._in_thread_run_script)
        defer.addBoth(self.cleanup)


    def _in_thread_run_script(self):
        """
        Run the script.
        """
        try:
            self.run_script()

        except Exception as e:
            # handle any exception thrown
            exc_type,exc_value,exc_traceback = sys.exc_info()
            print "Exception Error:  ",  exc_value
            print e

            # print traceback, excluding this file
            traceback.print_tb(exc_traceback)
            #exc_strings = traceback.format_list(traceback.extract_tb(exc_traceback))
            #exc_strings = [s for s in exc_strings if s.find("parlay_script.py")< 0 ]
            #for s in exc_strings:
            #    print s

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
    :param stop_reactor_on_close: Boolean regarding whether ot not to stop the reactor when the script closes\
     (Defaults to False if the reactor is running, True if the reactor is not currently running)
    :param skip_checks : if True will not do sanity checks on script (CAREFUL: BETTER KNOW WHAT YOU ARE DOING!)
    """
    if not skip_checks:
        if not issubclass(script_class, ParlayScript):
            raise TypeError("start_script called with: "+str(script_class)+" \n" +
                            "Can only call start_script on an instance of a subclass of ParlayScript")

    #set whether to stop the reactor or not (default to the opposite of reactor running)
    script_class.stop_reactor_on_close = stop_reactor_on_close if stop_reactor_on_close is not None else not reactor.running

    #connect it up
    factory = WebSocketClientFactory("ws://" + engine_ip + ":" + str(engine_port))
    factory.protocol = script_class
    reactor.connectTCP(engine_ip, engine_port, factory)

    if not reactor.running:
        reactor.run()



