from twisted.internet import reactor
from parlay_script import WebSocketClientFactory, ParlayScript, DEFAULT_ENGINE_WEBSOCKET_PORT
from threading import Thread
import inspect
import time
from txaio.tx import _get_loop

#get the script name importing me so it can have an ID
script_name = inspect.stack()[0][1]
global script, THREADED_REACTOR
THREADED_REACTOR = reactor
THREADED_REACTOR.getThreadPool()
loop = _get_loop()

class ThreadedParlayScript(ParlayScript):
    def _start_script(self):
        self._ready = True
        # do nothing. This is just an appliance class that doesn't run anything
        pass

#def a websocket factory to give this instance out on connection
class ScriptWebSocketFactory(WebSocketClientFactory):

    def buildProtocol(self, addr):
        #WebSocketClientFactory.buildProtocol(self,addr)
        #p = ThreadedParlayScript(script_name,script_name, THREADED_REACTOR)
        p = script
        p.factory = self
        return p

script = ThreadedParlayScript(script_name, script_name, THREADED_REACTOR)
script._ready = False

def start_reactor(engine_ip, engine_port):
    try:
        global THREADED_REACTOR
        #This is the reactor we will be using in a separate thread

        factory = ScriptWebSocketFactory("ws://" + engine_ip + ":" + str(engine_port), reactor=THREADED_REACTOR)
        THREADED_REACTOR.connectTCP(engine_ip, engine_port, factory)
        THREADED_REACTOR._registerAsIOThread = False
        THREADED_REACTOR.run(installSignalHandlers=False)
        print "DONE REACTING"
    except Exception as e:
        print e

def setup(engine_ip='localhost', engine_port=DEFAULT_ENGINE_WEBSOCKET_PORT):
    global script, THREADED_REACTOR
    # **ON IMPORT** start the reactor in a separate thread
    if not THREADED_REACTOR.running:
        r = Thread(target=start_reactor, args=(engine_ip, engine_port))
        r.daemon = True
        r.start()
        # wait till we're ready
        while THREADED_REACTOR is None or (not THREADED_REACTOR.running) or not script._ready:
            time.sleep(0.001)

        print script

