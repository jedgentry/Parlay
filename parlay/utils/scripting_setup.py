from parlay.server.reactor import reactor
from parlay_script import WebSocketClientFactory, ParlayScript, DEFAULT_ENGINE_WEBSOCKET_PORT
from threading import Thread
import inspect
import time
import datetime
global script, THREADED_REACTOR

# get the script name importing me so it can have an ID
script_name = inspect.stack()[0][1]


THREADED_REACTOR = reactor
THREADED_REACTOR.getThreadPool()


class ThreadedParlayScript(ParlayScript):

    def _start_script(self):
        self._ready = True
        # do nothing. This is just an appliance class that doesn't run anything
        pass


# define a websocket factory to give this instance out on connection
class ScriptWebSocketFactory(WebSocketClientFactory):

    def buildProtocol(self, addr):
        p = script
        p.factory = self
        return p


script = ThreadedParlayScript(script_name, script_name, THREADED_REACTOR)
script._ready = False


def start_reactor(ip, port):
    try:
        global THREADED_REACTOR
        # This is the reactor we will be using in a separate thread

        factory = ScriptWebSocketFactory("ws://" + ip + ":" + str(port), reactor=THREADED_REACTOR)
        THREADED_REACTOR.connectTCP(ip, port, factory)
        THREADED_REACTOR._registerAsIOThread = False
        THREADED_REACTOR.run(installSignalHandlers=False)
        print "DONE REACTING"
    except Exception as e:
        print e


def setup(ip='localhost', port=DEFAULT_ENGINE_WEBSOCKET_PORT, timeout=3):
    """
    Connect this script to the broker's websocket server.

    :param ip: ip address of the broker websocket server
    :param port: port of the broker websocket server
    :param timeout: try for this long to connect to broker before giving up
    :return: none
    """
    global script, THREADED_REACTOR
    # **ON IMPORT** start the reactor in a separate thread
    if not THREADED_REACTOR.running:
        r = Thread(target=start_reactor, args=(ip, port))
        r.daemon = True
        r.start()
        # wait till we're ready
        start = datetime.datetime.now()
        print "Connecting to", ip, ":", port
        while THREADED_REACTOR is None or (not THREADED_REACTOR.running) or not script._ready:
            time.sleep(0.001)
            if (datetime.datetime.now() - start).total_seconds() > timeout:
                raise RuntimeError("Could not connect to parlay. Is the parlay system running?")
