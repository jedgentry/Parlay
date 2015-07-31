from parlay.protocols.protocol import BaseProtocol
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from parlay.server.broker import Broker
import json
from twisted.internet import defer

class ParlayWebSocketProtocol(WebSocketServerProtocol, BaseProtocol):
    """
    When a client connects over a websocket, this is the protocol that will handle the communication.
    The messages are encoded as a JSON string
    """

    broker = Broker.get_instance()

    _discovery_response_defer = None

    def onClose(self, wasClean, code, reason):
        #clean up after ourselves
        self.broker.unsubscribe_all(self)
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
            #if we're not waiting for discovery, or if we are but it's not a didscovery message)
            if self._discovery_response_defer is None or \
                            msg['topics'].get('response', None) != 'get_protocol_discovery_response':
                self.broker.publish(msg, self.send_message_as_JSON)
            else:
                # discovery!
                self._discovery_response_defer.callback(msg['contents'].get('discovery', []))
                self._discovery_response_defer = None
        else:
            print "Binary messages not supported yet"



    def onConnect(self, request):
        #let the broker know we exist!
        self.broker.protocols.append(self)

    def get_discovery(self):

        # already in the middle of discvoery
        if self._discovery_response_defer is not None:
            return self._discovery_response_defer

        self.send_message_as_JSON({'topics': {'type': 'get_protocol_discovery'}, 'contents': {}})
        self._discovery_response_defer = defer.Deferred()

        def timeout():
            if self._discovery_response_defer is not None:
                # call back with nothing if timeout
                self._discovery_response_defer.callback([])
                self._discovery_response_defer = None

        self.broker._reactor.callLater(2, timeout)

        return self._discovery_response_defer

