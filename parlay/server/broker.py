
from twisted.internet import reactor
import json
from parlay.protocols.protocol import BaseProtocol
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

class Broker(object):
    """
    The Dispatcher is the sole holder of global state. There should be only one.
    It also coordinates all communication between protcols
    """
    instance = None

    def __init__(self, reactor):
        assert(Broker.instance is None)

        #the currently connected protocols
        self.protocols = []

        #The listeners that will be called whenever a message is received
        self._listeners = {}  # See Listener lookup document for more info

        self._reactor = reactor

        #THERE CAN BE ONLY ONE
        Broker.instance = self

    @staticmethod
    def get_instance():
        """
        @rtype Broker
        """
        if Broker.instance is None:
            Broker.instance = Broker(reactor)

        return Broker.instance

    def send_msg(self, msg):
        """
        Send a message out to the ecosystem
        """
        return self._call_listeners(msg)

    def _call_listeners(self, msg, root_list=None):
        """
        Call all of the listeners that match msg

        Time Complexity is O(2*n) * O(k)
        where:  n = the number of levels of the listener list
                k = the number of keys in the msg

        TODO: Remake this in super-fast Cython as a Trie
        """
        if root_list is None: root_list = self._listeners
        #call any functions in the None key
        for func, owner in root_list.get(None, []):
            func(msg)

        topics = msg['topics']
        #for each key in the listeners list
        for k in topics.keys():
            #if the key exists and  values match, then call any functions
            #or look further
                                  # root_list[k] is the value, which is a key to another dictionary
                                 #The None key in that dictionary will contain a list of funcs to call
                                # (Any other key will lead to yet another dictionary of keys and values)
            if k in root_list and topics[k] in root_list[k]:
                #recurse
                self._call_listeners(msg, root_list[k][topics[k]])


    def subscribe_listener(self, func, owner, **kwargs):
        """
        Register a listener. The kwargs is a dictionary of args that **all** must be true
        to call this listener. You may register the same function multiple times with different
        kwargs, and it may be called multiple times for each message.
        @param func: The function to run
        @param owner: The 'owner' of this function. This object can be passed to unsubscribe_all to remove this (e.g. on a protocol disconnect)
        @param kwargs: The key/value pairs to listen for
        """

        #sort so we always get the same order
        keys = sorted(kwargs.keys())
        root_list = self._listeners
        for k in keys:
            v = kwargs[k]

            if k not in root_list:
                root_list[k] = {}
            if v not in root_list[k]:
                root_list[k][v] = {}
            #go down a level
            root_list = root_list[k][v]

        #now that we're done, we have the leaf in root_list. Append it to the None list
        listeners = root_list.get(None, [])
        listeners.append((func, owner))
        root_list[None] = listeners


    def unsubscribe_all(self, owner, root_list = None):
        """
        Unsubscribe all function in our list that have a n owner that matches 'owner'
        """
        if root_list is None:
            root_list = self._listeners

        if None in root_list:   # don't bother checking if thre's no listeners here
            root_list[None] = [x for x in root_list[None] if x[1] != owner]

        for k in root_list:
            if k is not None:  # special key for listener list
                for v in root_list[k]:
                        #call it again
                        self.unsubscribe_all(owner, root_list[k][v])



    def get_modules(self):
        """
        Get the Discovery for everything
        """
        return [p.get_module() for p in self.protocols]



    def run(self):
        """
        Start up and run the broker. This method call with not return
        """
        #listen for websocket connections on port 8085
        factory = WebSocketServerFactory("ws://localhost:8085")
        factory.protocol = BrokerWebsocketBaseProtocol

        self._reactor.listenTCP(8085, factory)
        self._reactor.run()


class BrokerWebsocketBaseProtocol(WebSocketServerProtocol, BaseProtocol):
    """
    When a client connects over a websocket, this is the protocol that will handle the communication
    """


    def onConnect(self, request):
        self.broker = Broker.get_instance()

        #automatically subscribe to subcription types
        self.broker.subscribe_listener(self._on_subscribe_msg, self, type='subscribe', event='request')

    def onClose(self, wasClean, code, reason):
        #clean up after ourselves
        self.broker.unsubscribe_all(self)

    def _on_subscribe_msg(self, msg):
        #send a message when we get these

        self.broker.subscribe_listener(self.send_message_as_JSON, self, **(msg['contents']['topic']))
        resp_msg = msg.copy()
        resp_msg['topics']['event'] = 'reply'
        resp_msg['contents']['status'] = 'ok'

        #send the reply
        self.sendMessage(json.dumps(resp_msg))

    def send_message_as_JSON(self, msg):
        """
        Send a mesage dictionary as JSON
        """
        print("Sending")
        self.sendMessage(json.dumps(msg))

    def onMessage(self, payload, isBinary):
        if not isBinary:
            print payload
            msg = json.loads(payload)
            self.broker._call_listeners(msg)
        else:
            print "Binary messages not supported yet"








if __name__=="__main__":
    d = Broker(reactor)
    print "Hello Broker"
    d.run()