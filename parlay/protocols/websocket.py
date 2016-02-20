from parlay.protocols.base_protocol import BaseProtocol
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
        self.broker.protocols.append(self)

    def get_discovery(self):

        # already in the middle of discvoery
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
