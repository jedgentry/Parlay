from parlay.protocols.base_protocol import BaseProtocol
from parlay.server.adapter import Adapter
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketServerProtocol, WebSocketClientProtocol
from parlay.server.broker import Broker
import json
from twisted.internet import defer
from twisted.internet.protocol import Factory


class ParlayWebSocketProtocol(WebSocketServerProtocol, BaseProtocol):
    """
    When a client connects over a websocket, this is the protocol that will handle the communication.
    The messages are encoded as a JSON string
    """

    broker = Broker.get_instance()

    _discovery_response_defer = None

    def __init__(self):
        WebSocketServerProtocol.__init__(self)
        BaseProtocol.__init__(self)

    def onClose(self, wasClean, code, reason):
        print "Closing:" + str(self)
        # clean up after ourselves
        self.broker.untrack_protocol(self)
        self.broker._clean_trie()

    def send_message_as_JSON(self, msg):
        """
        Send a message dictionary as JSON
        """
        print("->" + str(msg))
        self.sendMessage(json.dumps(msg))

    def onMessage(self, payload, isBinary):
        if not isBinary:
            print payload
            msg = json.loads(payload)

            # if we're not waiting for discovery, or if we are but it's not a discovery message)
            if self._discovery_response_defer is None or \
                    msg['TOPICS'].get('type', None) != 'get_protocol_discovery_response':

                self.broker.publish(msg, self.send_message_as_JSON)

            else:
                # discovery!
                # get skeleton
                discovery = BaseProtocol.get_discovery(self)

                # fill with discovered children
                discovery['CHILDREN'] = msg['CONTENTS'].get('discovery', [])
                self._discovery_response_defer.callback(discovery)
                self._discovery_response_defer = None
        else:
            print "Binary messages not supported yet"

    def onConnect(self, request):
        # let the broker know we exist!
        self.broker.track_protocol(self)

    def get_discovery(self):
        # already in the middle of discovery
        if self._discovery_response_defer is not None:
            return self._discovery_response_defer

        self._discovery_response_defer = defer.Deferred()
        self.send_message_as_JSON({'TOPICS': {'type': 'get_protocol_discovery'}, 'CONTENTS': {}})

        def timeout():
            if self._discovery_response_defer is not None:
                # call back with nothing if timeout
                self._discovery_response_defer.callback({})
                self._discovery_response_defer = None

        self.broker._reactor.callLater(10, timeout)

        return self._discovery_response_defer

    def __str__(self):
        return "Websocket at " + str(self.peer)


class WebsocketAdapter(Adapter, WebSocketClientProtocol):
    """
    Connect a Python item to the Broker over a Websocket
    """

    def __init__(self):
        WebSocketClientProtocol.__init__(self)
        Adapter.__init__(self)
        self._subscribe_q = []
        self._listener_list = []  # no way to unsubscribe. Subscriptions last

    def onConnect(self, request):
        WebSocketClientProtocol.onConnect(self, request)
        self._connected.callback(True)
        #flush our subscription requests
        for _fn, topics in self._subscribe_q:
            self.subscribe(_fn, **topics)
        self._subscribe_q = []  # empty the list

    def call_on_every_message(self, listener):
        self._subscribe_q.append(listener)

    def onMessage(self, packet, isBinary):
        """
        We got a message.  See who wants to process it.
        """
        if isBinary:
            print "WebsocketBrokerProtocol doesn't understand binary messages"
            return

        msg = json.loads(packet)
        # run it through the listeners for processing
        for fn in self._listener_list:
            fn(msg)

    def subscribe(self, _fn=None, **topics):
        """
        Subscribe to messages the topics in **kwargs
        """
        #wait until we're connected to subscribe
        if not self.connected:
            self._subscribe_q.append((_fn, topics))
            return

        self.publish({"TOPICS": {'type': 'subscribe'}, "CONTENTS": {'TOPICS': topics}})
        if _fn is not None:
            def listener(msg):
                topics = msg["TOPICS"]
                if all(k in topics and v == topics[k] for k, v in topics.iteritems()):
                    _fn(msg)

            self._listener_list.append(listener)

    def publish(self, msg):
        if not self.connected:
            raise RuntimeError("Not Connected to Broker yet")
        self.sendMessage(json.dumps(msg))


class WebsocketAdapterFactory(WebSocketClientFactory):
    def __init__(self, *args, **kwargs):
        self.adapter = WebsocketAdapter()  # this is the adapter singleton
        WebSocketClientFactory.__init__(self, *args, **kwargs)

    def buildProtocol(self, addr):
        adapter = self.adapter
        adapter.factory = self

        return adapter

