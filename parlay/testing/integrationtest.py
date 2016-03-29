"""
Integration tests are when you want to use Parlay to test *something external*. It could be a simulator, or a real
device hooked up over a protocol. Either way, the broker must already be running, and the connections established before
running the Integration test
"""

import unittest
from parlay import utils
import multiprocessing
import parlay

def start_broker():
    p = multiprocessing.Process(target=parlay.start)

def stop_broker():
    utils.shutdown_broker()


class TestCase(unittest.TestCase):
    """
    An integration test case is like a unittest test case, and uses the same reporting mechanisms.
    """
    pass