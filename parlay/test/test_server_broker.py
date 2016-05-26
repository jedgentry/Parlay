from twisted.trial import unittest
from twisted.internet import defer
from parlay.server.broker import Broker

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
