"""
ParlayCloud link item.  This tem offers communcation and other services to help communicate this Item with the Cloud
"""
from twisted.python import log
import sys
log.startLogging(sys.stdout)
import parlay
from parlay.server.broker import Broker, run_in_thread
from twisted.internet.threads import blockingCallFromThread
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
import base64
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketServerProtocol, WebSocketClientProtocol, connectWS
import requests
import json
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode
from twisted.internet import ssl
import time


class CloudLinkSettings(object):
    """
    Class level settings to set for cloudLink
    """
    PRIVATE_KEY_LOCATION = None
    PRIVATE_KEY_PASSPHRASE = None  # can be none, but I recommend a passphrase anyway. It may or may not be more secure


@parlay.local_item()
class CloudLink(parlay.ParlayCommandItem):

    connected_to_cloud = parlay.ParlayProperty(val_type=bool, default=False, read_only=True)
    base_link_uri = parlay.ParlayProperty(val_type=str, default="https://dev.parlay.cloud/channels")
    #base_link_uri = parlay.ParlayProperty(val_type=str, default="http://localhost:5056/channels")

    def __init__(self):
        parlay.ParlayCommandItem.__init__(self, "parlay.items.cloud_link", "Cloud Link")
        self._http_agent = Agent(self._reactor)
        self.channel_uri = None
        self.uuid = None
        self.cloud_factory = None
        if CloudLinkSettings.PRIVATE_KEY_LOCATION is None:
            raise RuntimeError("CloudLinkSettings.PRIVATE_KEY_LOCATION must be set for cloud to work")

    @parlay.parlay_command(async=True)
    def http_request(self, path="/", encode='zlib'):
        """
        Do an http request on the broker
        :type path str
        """
        url = "http://localhost:" + str(Broker.get_instance().http_port)+path
        print url
        # http"://localhost:broker.http_port
        request = self._http_agent.request(
            'GET',
            url,
            Headers({'User-Agent': ['Twisted Web Client']}),
            None)
        request.addCallback(lambda response: readBody(response))
        request.addCallback(lambda html: (base64.b64encode(html.encode(encode))) if encode == "zlib" else html)
        return request

    @parlay.parlay_command(async=True)
    def connect_to_cloud_channel(self, uuid):
        """
        Connect up to the cloud channel with UUID uuid
        :param uuid: the UUID of this device. The uuid determines which channel you are connected to
        :return:
        """
        if self. connected_to_cloud:
            raise RuntimeError("Already Connected to cloud")

        self.uuid = uuid.strip()

        yield self.get_channel()
        # cool, now set up the websocket connection to that channel
        reactor = self._adapter.reactor
        #self.channel_uri = "ws" + self.channel_uri[3:]
        print "attempting to connect to", self.channel_uri
        self.cloud_factory = CloudLinkWebsocketClientFactory(self, self.channel_uri,  reactor=reactor)
        self.cloud_factory.protocol = CloudLinkWebsocketClient
        if self.channel_uri.startswith("wss"):
            reactor.connectSSL(self.cloud_factory.host, self.cloud_factory.port, self.cloud_factory, ssl.ClientContextFactory())
        else:
            reactor.connectTCP(self.cloud_factory.host, self.cloud_factory.port, self.cloud_factory)

    @run_in_thread
    def get_channel(self):
        #first get a token we need to sign in order to prove we are who we say we are
        r = requests.get(str(self.base_link_uri) + "/get_device_token", params={"UUID": self.uuid, })

        token = r.json()["token"]
        # get the private Key
        with open(CloudLinkSettings.PRIVATE_KEY_LOCATION,'r') as key_file:
            private_key = RSA.importKey(key_file.read(),
                                        passphrase=CloudLinkSettings.PRIVATE_KEY_PASSPHRASE)


        # sign the token with our private key
        signature = PKCS1_v1_5.new(private_key).sign(SHA256.new(token))

        # get the randomly assigned channel for my UUID
        r = requests.get(str(self.base_link_uri) + "/get_device_group",
                         params={"UUID": self.uuid, "signature": b64encode(signature)})
        if r.ok:
            self.channel_uri = r.json()["channel"]
        elif r.status_code == 400:
            raise Exception("UUID or Token not registered with Cloud.")
        elif r.status_code == 403:
            raise Exception("Signature didn't verify correctly. Bad private key or signature.")



class CloudLinkWebsocketClientFactory(WebSocketClientFactory):
    """
    Websocket Client library that keeps track of the cloud item for the CloudLinkWebsocketClient
    """
    def __init__(self, cloud_item, *args, **kwargs):
        WebSocketClientFactory.__init__(self, *args, **kwargs)
        self.cloud_item = cloud_item


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

    def onConnect(self, response):
        print "Connected to cloud"
        self.factory.cloud_item.connected_to_cloud = True

    def connectionLost(self, reason):
        print "connection lost:", str(reason)
        self.factory.cloud_item.connected_to_cloud = False


    def onMessage(self, payload, isBinary):
        """
        When we get a message from the cloud link, publish it on our broker   PRIVATE_KEY_LOCATION
        `
        :param payload:
        :param isBinary:
        :return:
        """
        if isBinary:
            return  # Binary messages aren't supported

        try:
            msg = json.loads(payload)
            print msg

            # special logic for subscriptions. If we want to subscribe, then push it to the cloud
            if msg["TOPICS"].get('type') == 'subscribe':
                self._adapter.subscribe(self.send_message_to_cloud_channel, **(msg["CONTENTS"].get("TOPICS", {})))

            else:
                self._adapter.publish(msg, self.send_message_to_cloud_channel)
        except Exception as e:
            print "Exception on message" + str(payload) + "  " + str(e)

@parlay.local_item()
class CloudStressTest(parlay.ParlayCommandItem):

    data = parlay.ParlayDatastream(val_type=float, default=0.0)
    sleep_time = parlay.ParlayProperty(val_type=float, default=1)

    @parlay.parlay_command()
    def count_up(self, max):
        """

        :param max:
        :type max int
        :return:
        """
        for x in xrange(max):
            self.data = x
            time.sleep(self.sleep_time)

if __name__ == "__main__":
    # if run as main entry point, setup test key files
    CloudLinkSettings.PRIVATE_KEY_LOCATION = '/home/varx/.ssh/test_parlay_device'
    CloudLinkSettings.PRIVATE_KEY_PASSPHRASE = None
    c = CloudLink()
    d = CloudStressTest()
    parlay.start(ui_path="/home/varx/Projects/Promenade/Parlay/ParlayUI/dist/")