"""
ParlayCloud link item.  This tem offers communcation and other services to help communicate this Item with the Cloud
"""

import parlay
from parlay.server.broker import Broker
from twisted.internet import reactor
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
import base64
import requests



@parlay.local_item()
class CloudLink(parlay.ParlayCommandItem):

    def __init__(self):
        parlay.ParlayCommandItem.__init__(self, "parlay.items.cloud_link", "Cloud Link")
        self._http_agent = Agent(self._reactor)

    @parlay.parlay_command(async=True)
    def http_request(self, path="/"):
        """
        Do an http request on the broker
        :type path str
        """
        url = "http://localhost:" + str(Broker.get_instance().http_port)+path
        # http"://localhost:broker.http_port
        request = self._http_agent.request(
            'GET',
            url,
            Headers({'User-Agent': ['Twisted Web Client Example']}),
            None)
        request.addCallback(lambda response: readBody(response))
        request.addCallback(lambda html: base64.b64encode(html.encode("zlib")))
        return request

    def submit_data_point(self):


    @parlay.parlay_command()

if __name__ == "__main__":
    c = CloudLink()
    parlay.start()