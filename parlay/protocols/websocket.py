from parlay.protocols.protocol import BaseProtocol
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from parlay.server.broker import Broker
import json

class BrokerWebsocketBaseProtocol(WebSocketServerProtocol, BaseProtocol):
    """
    When a client connects over a websocket, this is the protocol that will handle the communication.
    The mesasge are encoded as a JSON string
    """

    broker = Broker.get_instance()



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
            self.broker.publish(msg, self.send_message_as_JSON)
        else:
            print "Binary messages not supported yet"
