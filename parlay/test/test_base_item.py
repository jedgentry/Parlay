from twisted.trial import unittest
from parlay.testing.unittest_mixins.adapter import AdapterMixin
from parlay.testing.unittest_mixins.reactor import ReactorMixin

from parlay.items import base


class BaseItemTest(unittest.TestCase, AdapterMixin, ReactorMixin):

    def setUp(self):
        # Parent initializations
        self.first_parent = base.BaseItem("First Parent", "First Parent", adapter=self.adapter)
        self.second_parent = base.BaseItem("Second Parent", "Second Parent", adapter=self.adapter)

        # Child initializations
        self.one_parent_child = base.BaseItem("1-Parent Child", "1-Parent Child",
                                              adapter=self.adapter, parents=self.first_parent)
        self.two_parent_child = base.BaseItem("2-Parent Child", "2-Parent Child",
                                              adapter=self.adapter, parents=[self.first_parent, self.second_parent])
        # Create item with zero parents
        self.no_parent_child = base.BaseItem("No-Parent Child", "No-Parent Child",
                                             adapter=self.adapter)
        # Create item with no children
        self.no_children = base.BaseItem("No-Children Item", "No-Children Item", adapter=self.adapter)

    def testTwoChildrenDiscovery(self):

        # self.first_parent should have two children. 1-Parent child and 2-Parent child.
        expected_discovery = {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': 'First Parent',
                              'CHILDREN': [{'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': '1-Parent Child',
                                            'CHILDREN': [], 'ID': '1-Parent Child'},
                                           {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': '2-Parent Child',
                                            'CHILDREN': [], 'ID': '2-Parent Child'}], 'ID': 'First Parent'}
        self.assertEqual(self.first_parent.get_discovery(), expected_discovery)

    def testNoParentDiscovery(self):

        expected_discovery = {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': 'No-Parent Child',
                              'CHILDREN': [], 'ID': 'No-Parent Child'}
        self.assertEqual(expected_discovery, self.no_parent_child.get_discovery())

    def testTwoParentDiscovery(self):

        expected_discovery = {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': '2-Parent Child',
                              'CHILDREN': [], 'ID': '2-Parent Child'}
        self.assertEqual(expected_discovery, self.two_parent_child.get_discovery())

    def testSingleChildDiscovery(self):

        expected_discovery = {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': 'Second Parent',
                              'CHILDREN': [{'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': '2-Parent Child',
                                            'CHILDREN': [], 'ID': '2-Parent Child'}], 'ID': 'Second Parent'}
        self.assertEqual(expected_discovery, self.second_parent.get_discovery())

    def testNoChildren(self):

        expected_discovery = {'INTERFACES': [], 'TYPE': 'BaseItem/object', 'NAME': 'No-Children Item',
                              'CHILDREN': [], 'ID': 'No-Children Item'}
        self.assertEqual(expected_discovery, self.no_children.get_discovery())