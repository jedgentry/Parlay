from twisted.trial import unittest
from twisted.internet import defer
from twisted.web import static, server
from twisted.web.test.requesthelper import DummyChannel

from parlay.server.broker import Broker, PARLAY_PATH
from parlay.server.http_server import CacheControlledSite, FRESHNESS_TIME_SECS


class BrokerPubSubTests(unittest.TestCase):

    def setUp(self):
        self._broker = Broker.get_instance()

    def testSimplePubSub(self):
        sub_called = defer.Deferred()
        def sub_me(msg):
            sub_called.callback(msg)

        self._broker.subscribe(sub_me, self, simple_unit_test=True)
        self._broker.publish({"TOPICS": {"simple_unit_test": True}, "CONTENTS": {}})
        self.assertTrue(sub_called.called)

    def testSimplePubSubNotPub(self):
        sub_called = defer.Deferred()
        def sub_me(msg):
            sub_called.callback(msg)

        self._broker.subscribe(sub_me, self, simple_unit_test_not_called=True)
        self._broker.publish({"TOPICS": {"simple_unit_test": True}, "CONTENTS": {}})
        self.assertTrue(not sub_called.called)

    def tearDown(self):
        # always use self as the owner of any subscriptions so that this single call will clean it up
        self._broker.unsubscribe_all(self)


class CacheControlledSiteTest(unittest.TestCase):
    def setUp(self):
        self._resource = static.File(PARLAY_PATH + "/ui/dist")

    def testNoUICaching(self):
        ui_caching = False
        site = CacheControlledSite(ui_caching, self._resource)
        request = server.Request(DummyChannel(), False)
        request.prepath = [b""]
        request.postpath = [b""]
        site.getResourceFor(request)
        assert(request.responseHeaders.getRawHeaders("cache-control") == ["no-store, must-revalidate"])

    def testUICaching(self):
        ui_caching = True
        site = CacheControlledSite(ui_caching, self._resource)
        request = server.Request(DummyChannel(), False)
        request.prepath = [b""]
        request.postpath = [b""]
        site.getResourceFor(request)
        assert(request.responseHeaders.getRawHeaders("cache-control") == ["max-age={}".format(FRESHNESS_TIME_SECS)])
