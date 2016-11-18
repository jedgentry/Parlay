"""
ParlayCloud link item.  This tem offers communcation and other services to help communicate this Item with the Cloud
"""

import parlay
from parlay.server.broker import Broker
from twisted.internet import reactor
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
import base64
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketServerProtocol, WebSocketClientProtocol
import requests
import json

@parlay.local_item()
class CloudLink(parlay.ParlayCommandItem):

    base_link_uri = parlay.ParlayProperty(val_type=str, default="http://localhost:8000")

    def __init__(self):
        parlay.ParlayCommandItem.__init__(self, "parlay.items.cloud_link", "Cloud Link")
        self._http_agent = Agent(self._reactor)
        self.channel_uri = None

    @parlay.parlay_command(async=True)
    def http_request(self, path="/", encode='zlib'):
        """
        Do an http request on the broker
        :type path str
        """
        url = "http://localhost:" + str(Broker.get_instance().http_port)+path
        # http"://localhost:broker.http_port
        request = self._http_agent.request(
            'GET',
            url,
            Headers({'User-Agent': ['Twisted Web Client']}),
            None)
        request.addCallback(lambda response: readBody(response))
        request.addCallback(lambda html: (base64.b64encode(html.encode(encode))) if encode == "zlib" else html)
        return request

    @parlay.parlay_command()
    def connect_to_cloud_channel(self, uuid):
        """
        Connect up to the cloud channel with UUID uuid
        :param uuid: the UUID of this device. The uuid determines which channel you are connected to
        :return:
        """
        # get the randomly assigned channel for my UUID
        r = requests.get(str(self.base_link_uri) + "/get_channel", params={"UUID": uuid})
        # todo : encrypt the result with the PUBLIC key of this UUID, otherwise anyone could start an arbitrary conversation over a channel
        self.channel_uri = r.json()["channel"]
        # cool, now set up the websocket connection to that channel
        reactor = self._adapter.reactor
        factory = WebSocketClientFactory(self.channel_uri, reactor=reactor)
        factory.protocol = CloudLinkWebsocketClient
        reactor.connectTCP(factory.host, factory.port, factory)




class CloudLinkWebsocketClient(WebSocketClientProtocol):
    """
    The websocket client that will bridge all messages between the broker and the cloud channel
    """

    def __init__(self, adapter=None):
        WebSocketClientProtocol.__init__(self)
        self._adapter = adapter if adapter is not None else Broker.get_instance().pyadapter
        # subscribe our cloud bridge method to be called on ALL messages
        #self._adapter.subscribe(self.send_message_to_cloud_channel)

    def send_message_to_cloud_channel(self, msg):
        """
        Send the message to the cloud. This should be subscribed to all messages
        :param msg:
        :return:
        """
        self.sendMessage(json.dumps(msg))

    def onMessage(self, payload, isBinary):
        """
        When we get a message from the cloud link, publish it on our broker
        :param payload:
        :param isBinary:
        :return:
        """
        if isBinary:
            return # Binary messages aren't supported

        # special logic for subscriptions. If we want to subscribe, then push it to the cloud
        msg = json.loads(payload)
        if msg["TOPICS"].get('type') == 'subscribe':
            self._adapter.subscribe(self.send_message_to_cloud_channel, **(msg["CONTENTS"].get("TOPICS", {})))

        else:
            self._adapter.publish(msg)


if __name__ == "__main__":
    c = CloudLink()
    parlay.start()