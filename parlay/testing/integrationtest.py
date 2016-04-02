"""
Integration tests are when you want to use Parlay to test *something external*. It could be a simulator, or a real
device hooked up over a protocol. Either way, the broker must already be running, and the connections established before
running the Integration test
"""

import unittest
from parlay import utils
from parlay.utils import scripting_setup
from twisted.internet import defer
import multiprocessing
import parlay
from parlay.items.threaded_item import ListenerStatus

def start_broker():
    p = multiprocessing.Process(target=parlay.start)

def stop_broker():
    utils.shutdown_broker()


class TestCase(unittest.TestCase):
    """
    An integration test case is like a unittest test case, and uses the same reporting mechanisms.
    """

    def simulate_id(self, id):
        """
        Simulate a particular device so we can wait on the messages
        """
        # subscribe to messages with this ID
        scripting_setup.script.subscribe_to(TO=id)

    @scripting_setup.run_in_threaded_reactor
    def wait_for_message(self, from_id, to_id=None, timeout=30):
        """
        Wait for a message from from_id, and to to_id (or anyone if to_id is None)
        """
        d = defer.Deferred()
        timer = scripting_setup.THREADED_REACTOR.callLater(timeout, lambda: d.cancel())
        def listener(msg):
            if msg["TOPICS"].get("FROM", None) == from_id and (to_id is None or msg["TOPICS"].get("TO", None) == to_id):
                timer.cancel()
                d.callback(msg)
                return ListenerStatus.REMOVE_LISTENER
            else:
                return ListenerStatus.KEEP_LISTENER

        scripting_setup.script.add_listener(listener)
        return d


    def send_response(self, msg, contents=None, extra_topics=None):
        contents = contents if contents is not None else {}
        extra_topics = extra_topics if extra_topics is not None else {}

        scripting_setup.script.send
