from parlay.protocols.serial_line import USBASCIILineProtocol
from twisted.trial import unittest
from parlay.testing.unittest_mixins.reactor import ReactorMixin
from serial.tools.list_ports_common import ListPortInfo
import re


class USBASCIILineTest(unittest.TestCase, ReactorMixin):
    """
    Class used to test the USBASCIILineProtocol. This function aims to test the functionality of the helper functions
    in particular.
    """

    def setUp(self):
        """
        Overridden function from unittest.TestCase. This will be called before each test case is run.
        :return: None
        """
        self.protocol = USBASCIILineProtocol("USBASCIILineProtocol")
        self.fake_port_list = []
        unittest.TestCase.setUp(self)

    def testFilter(self):
        """
        Used to test the _match_usb_port() function. Test all positive and negative paths.
        :return: None
        """
        # Add one fake port to the list
        self._add_fake_port("STM32 STLink", 1155, 14155, "USB_PATH")
        # Test positive path.
        self.assertTrue(self.protocol._match_usb_port(self.fake_port_list[0], 1155, 14155, re.compile("STLink")))
        # Test negative path (no match)
        self.assertFalse(self.protocol._match_usb_port(ListPortInfo(), 1155, 14155, re.compile("STLink")))
        # Test alt. negative path (only regex doesn't match)
        self.assertFalse(self.protocol._match_usb_port(ListPortInfo(), 1155, 14155, re.compile("BADREGEX")))
        # Test alt. positive path (None for string)
        self.assertTrue(self.protocol._match_usb_port(self.fake_port_list[0], 1155, 14155, None))
        # Test alt. negative path (Vendor ID doesn't match but product ID does)
        self.assertFalse(self.protocol._match_usb_port(self.fake_port_list[0], 0xFFF, 14155, None))
        # Test alt. negative path (Product ID doesn't match but vendor ID does)
        self.assertFalse(self.protocol._match_usb_port(self.fake_port_list[0], 1155, 0xFFF, None))
        # Test true negative path (nothing matches, w/ None)
        self.assertFalse(self.protocol._match_usb_port(self.fake_port_list[0], 0xFFF, 0xFFF, None))
        # Test true negative path (nothing matches)
        self.assertFalse(self.protocol._match_usb_port(self.fake_port_list[0], 0xFFF, 0xFFF, re.compile("NOMATCH")))
        self._clear_fake_ports()

    def testListFiltering(self):
        """
        Used to test the _filter_ports() functions. Test all negative and positive paths.
        :return:
        """
        self._add_fake_port("COM5 USB SERIAL", 1155, 14155, "USB_PATH")
        self._add_fake_port("COM5 USB SERIAL", 1155, 14155, "USB_PATH")

        # Test alt. negative path (multiple matches)
        self.assertEqual(["USB_PATH", "USB_PATH"], self.protocol._filter_ports(self.fake_port_list, 1155, 14155,
                                                                               re.compile("USB SERIAL")))
        self._clear_fake_ports()
        self._add_fake_port("STM32 STLink", 1155, 14155, "USB_PATH")
        self.assertEqual(["USB_PATH"], self.protocol._filter_ports(self.fake_port_list, 1155, 14155,
                                                                               re.compile("STLink")))
        self.assertEqual([], self.protocol._filter_ports(self.fake_port_list, 1155, 14155,
                                                                               re.compile("BADREGEX")))

    def _add_fake_port(self, description, vid, pid, usb_path):
        """
        Helper function used to add a port to our "fake" ports list that we will be operating on. This is needed
        because we can't rely on the list_ports.comports() function for unit testing since it directly interfaces
        with hardware.
        :param description: string description that the fake port will have
        :param vid: vendor ID that the fake port will have
        :param pid: product ID that the fake port will have
        :param usb_path: device (or path) that the fake port will have
        :return:
        """
        fake_port = ListPortInfo()
        fake_port.description = description
        fake_port.pid = pid
        fake_port.vid = vid
        fake_port.device = usb_path
        self.fake_port_list.append(fake_port)

    def _remove_fake_port(self, description):
        """
        Removes a port from our "fake" port list.
        :param description: description string of the port we want to remove.
        :return:
        """
        for port in list(self.fake_port_list):
            if description == port.description:
                self.fake_port_list.remove(port)

    def _clear_fake_ports(self):
        """
        Resets our "fake" port list.
        :return:
        """
        self.fake_port_list = []
