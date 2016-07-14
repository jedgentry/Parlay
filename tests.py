# integration test

from twisted.trial import unittest  # import the standard python unitest framework
from twisted.internet import reactor
from parlay import utils
import parlay
# init the parlay script. This ony needs to be done once
##from adder import Adder
#from combiner import Combiner
#from multiplier import Multiplier



class TestAdder(unittest.TestCase):

    def setUp(self):
        parlay.start_for_test()
        # connect your protocols here
        #a = Adder()
        #c = Combiner()
        #m = Multiplier()
        #utils.setup()
        utils.discover()
        # get your handles
        #self.a = utils.get_item_by_name("Adder")
        #self.c = utils.get_item_by_name("Combiner")
        #self.m = utils.get_item_by_name("Multiplier")

    def teardown(self):

        parlay.stop_for_test()

    def test_add(self):
        """
        Any method in a testcase starting with 'test' will be run as a unit test
        """

        result = self.a.add(1, 3)
        # make sure 1 + 3 = 4
        self.assertEqual(result, 4)  # this will fail the test if result != 4

    def test_commutativity(self):
        """
        Each test method is a python method, and can do anything python can do during a test
        """
        for i in range(20):
            for j in range(20):
                result1 = self.a.add(i, j)
                result2 = self.a.add(j, i)
                self.assertEqual(result1, result2)

    def test_negative(self):
        """
        Theres' many different assert options.
        See the docs for more info at: See https://docs.python.org/2/library/unittest.html
        """
        result = self.a.add(10, -100)
        self.assertLess(result, 0)
