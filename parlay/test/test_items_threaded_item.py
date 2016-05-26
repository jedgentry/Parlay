from twisted.trial import unittest
from twisted.internet import defer
from twisted.internet.task import Clock
from parlay.server.broker import Broker
from parlay.testing.unittest_mixins.adapter import AdapterMixin
from parlay.testing.unittest_mixins.reactor import ReactorMixin

from parlay.items import threaded_item

class ThreadedItemTest(unittest.TestCase, AdapterMixin, ReactorMixin):

    def setUp(self):
        self.item = threaded_item.ThreadedItem("TEST_ITEM", "TEST_ITEM", reactor=self.reactor, adapter=self.adapter)

    def testDiscovery(self):
        self.item.discover(force=True)
        expected = {"TOPICS": {'type': 'broker', 'request': 'get_discovery'}, "CONTENTS": {'force': True}}
        self.assertEqual(self.adapter.last_published, expected)

    def tearDown(self):
        pass
