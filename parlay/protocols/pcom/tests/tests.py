from pcom_message import PCOMMessage
import struct
import serial_encoding
from pcom_serial import PCOM_Serial
from twisted.internet import defer
from twisted.trial import unittest

from parlay.testing.unittest_mixins.adapter import AdapterMixin
from parlay.testing.unittest_mixins.reactor import ReactorMixin


class TestSerialEncoding(unittest.TestCase):
    b_msg_id = 20
    b_source_id = 5
    b_destination_id = 7
    b_order_code = 1001
    b_type = "COMMAND"
    b_attributes = 0x01
    b_format_string = ''
    b_incoming_data = []
    b_status = 0

    b_contents = {"COMMAND": 1001}
    s = PCOMMessage(msg_id=b_msg_id, from_=b_source_id, to=b_destination_id,
                    response_code=b_order_code, msg_type=b_type, attributes=b_attributes, msg_status=b_status,
                    data_fmt=b_format_string, data=b_incoming_data, contents=b_contents)

    def test_binary_unpacking(self):
        raise unittest.SkipTest("skipping need to handle msg_Status")

        b_msg = serial_encoding.encode_pcom_message(self.s)
        msg = serial_encoding.decode_pcom_message(b_msg)

        self.assertEqual(msg.msg_id, self.b_msg_id)
        self.assertEqual(msg.from_, self.b_source_id)
        self.assertEqual(msg.to, self.b_destination_id)
        self.assertEqual(msg.response_code, self.b_order_code)
        # self.assertEqual(msg.msg_type, self.b_type)
        self.assertEqual(msg.attributes, self.b_attributes)
        self.assertEqual(msg.format_string, '')
        self.assertEqual(msg.data, [])

        self.s.format_string = "B"
        self.s.data = [0x10]

        b_msg = serial_encoding.encode_pcom_message(self.s)
        msg = serial_encoding.decode_pcom_message(b_msg)

        self.assertEqual(msg.msg_id, self.b_msg_id)
        self.assertEqual(msg.from_, self.b_source_id)
        self.assertEqual(msg.to, self.b_destination_id)
        self.assertEqual(msg.response_code, self.b_order_code)
        # self.assertEqual(msg.msg_type, self.b_type)
        self.assertEqual(msg.attributes, self.b_attributes)
        self.assertEqual(msg.format_string, "B")
        self.assertEqual(msg.data, [0x10])

        self.s.format_string = "fB"
        self.s.data = [0x10, 0x14]

        b_msg = serial_encoding.encode_pcom_message(self.s)
        msg = serial_encoding.decode_pcom_message(b_msg)

        self.assertEqual(msg.msg_id, self.b_msg_id)
        self.assertEqual(msg.from_, self.b_source_id)
        self.assertEqual(msg.to, self.b_destination_id)
        self.assertEqual(msg.response_code, self.b_order_code)
        # self.assertEqual(msg.msg_type, self.b_type)
        self.assertEqual(msg.attributes, self.b_attributes)
        self.assertEqual(msg.format_string, "fB")
        self.assertEqual(msg.data, [0x10, 0x14])

        self.s.format_string = "ffbBH"
        self.s.data = [0x01, 0x01, 0x01, 0x01, 0x01]

        b_msg = serial_encoding.encode_pcom_message(self.s)
        msg = serial_encoding.decode_pcom_message(b_msg)

        self.assertEqual(msg.msg_id, self.b_msg_id)
        self.assertEqual(msg.from_, self.b_source_id)
        self.assertEqual(msg.to, self.b_destination_id)
        self.assertEqual(msg.response_code, self.b_order_code)
        # self.assertEqual(msg.msg_type, self.b_type)
        self.assertEqual(msg.attributes, self.b_attributes)
        self.assertEqual(msg.format_string, "ffbBH")
        self.assertEqual(msg.data, [1.0, 1.0, 1, 1, 1])

    def test_translate_format_string(self):
        self.assertEqual('B4s', serial_encoding.translate_fmt_str('Bs', '\x12\x65\x65\x65\x00'))
        self.assertEqual('H4s', serial_encoding.translate_fmt_str('Hs', [12, "car"]))
        self.assertEqual('2H4s', serial_encoding.translate_fmt_str('2Hs', [12, 14, "car"]))
        self.assertEqual('2B4s', serial_encoding.translate_fmt_str('2Bs', '\x12\x14\x65\x65\x65\x00'))
        self.assertEqual('2b2H4s', serial_encoding.translate_fmt_str('2b2Hs', [12, 13, 14, 15, "car"]))
        self.assertEqual('2H4s', serial_encoding.translate_fmt_str('2Hs', '\x12\x13\x14\x15\x65\x65\x65\x00'))
        self.assertEqual('5s', serial_encoding.translate_fmt_str('s', ["help"]))
        self.assertEqual('5s', serial_encoding.translate_fmt_str('s', '\x65\x65\x65\x65\x00'))
        self.assertEqual('2s', serial_encoding.translate_fmt_str('s', ["c"]))
        self.assertEqual('2s', serial_encoding.translate_fmt_str('s', '\x23\x00'))
        self.assertEqual('5s2B', serial_encoding.translate_fmt_str('s2B', '\x65\x65\x65\x65\x00\x12\x12'))
        self.assertEqual('6s2H', serial_encoding.translate_fmt_str('s2H', ["hello", 12, 2]))

    def test_cast_data(self):
        self.assertEqual([12, 13, 14], serial_encoding.cast_data("3H", ["12", "13", "14"]))
        self.assertEqual([1, 0, 1, 2, 2, 2, 2], serial_encoding.cast_data("3H4b", ["1", "0", "1", "2", "2", "2", "2"]))
        self.assertEqual(["hello"], serial_encoding.cast_data("s", ["hello"]))
        self.assertEqual([0, 0, 0, "hello"], serial_encoding.cast_data("3Hs", ["0", "0", "0", "hello"]))
        self.assertEqual([0, 0, "hello", 0, 0], serial_encoding.cast_data("2Hs2H", ["0", "0", "hello", "0", "0"]))
        self.assertEqual([12, "t", "s", 12], serial_encoding.cast_data("HssH", ["12", "t", "s", "12"]))
        self.assertEqual([12, 13, 14, 11, 0, 1, 2, 3],
                         serial_encoding.cast_data("2b2B2h2H", ["12", "13", "14", "11", "0", "1", "2", "3"]))
        self.assertEqual(['c', 32], serial_encoding.cast_data("cI", ["c", "32"]))


class TestPCOMMessage(unittest.TestCase):
    command_msg = {
        'TOPICS': {
            'TX_TYPE': "DIRECT",
            'MSG_TYPE': "COMMAND",
            'RESPONSE_REQ': True,
            'MSG_ID': 100,
            'MSG_STATUS': "OK",
            'FROM': 0xfefe,
            'TO': 260
        },
        'CONTENTS': {
            'COMMAND': 2000
        }
    }

    PROPERTY_MSG = {
        'TOPICS': {
            'TX_TYPE': None,
            'MSG_TYPE': None,
            'RESPONSE_REQ': None,
            'MSG_ID': None,
            'MSG_STATUS': None,
            'FROM': None,
            'TO': None
        },
        'CONTENTS': {
            'PROPERTY': None,
            'VALUE': None,
            'ACTION': None
        }
    }

    RESPONSE_MSG = {
        'TOPICS': {
            'TX_TYPE': None,
            'MSG_TYPE': None,
            'RESPONSE_REQ': None,
            'MSG_ID': None,
            'MSG_STATUS': None,
            'FROM': None,
            'TO': None
        },
        'CONTENTS': {
            'STATUS': None,
            'STATUS_NAME': None
        }
    }


class TestPCOMProtocol(unittest.TestCase, AdapterMixin, ReactorMixin):
    BAUD_RATE = 57600
    PORT_NAME = "/dev/cu.usbserial-FTHM129F"
    TEST_ITEM_ID = 0xfef1
    EMBEDDED_TEST_ID = 261
    MSG_ID_BASE = 10
    TEST_PROPERTY_ID = 3002

    STREAM_ON = {
        "TOPICS": {
            "TX_TYPE": "DIRECT",
            "MSG_TYPE": "STREAM",
            "TO": EMBEDDED_TEST_ID,
            "MSG_ID": MSG_ID_BASE,
            "FROM": TEST_ITEM_ID
        },

        "CONTENTS": {
            "STREAM": TEST_PROPERTY_ID,
            "STOP": False
        }
    }

    STREAM_OFF = {
        "TOPICS": {
            "TX_TYPE": "DIRECT",
            "MSG_TYPE": "STREAM",
            "TO": EMBEDDED_TEST_ID,
            "MSG_ID": MSG_ID_BASE+1,
            "FROM": TEST_ITEM_ID
        },

        "CONTENTS": {
            "STREAM": TEST_PROPERTY_ID,
            "STOP": True
        }
    }

    EXPECTED_RESPONSE = {
        'TOPICS': {
            'STREAM': TEST_PROPERTY_ID,
            'FROM': EMBEDDED_TEST_ID,
            'MSG_STATUS': 'OK',
            'MSG_TYPE': 'STREAM',
            'MSG_ID': MSG_ID_BASE,
            'TO': TEST_ITEM_ID,
            'RESPONSE_REQ': False,
            'TX_TYPE': 'DIRECT'
        },
        'CONTENTS': {
            'STATUS': 0,
            'RATE': 1000,
            'VALUE': 1
        }
    }

    PROPERTY_GET = {
        "TOPICS": {
            "TX_TYPE": "DIRECT",
            "MSG_TYPE":"PROPERTY",
            "TO": EMBEDDED_TEST_ID,
            "MSG_ID": MSG_ID_BASE+2,
            "FROM": TEST_ITEM_ID
        },
        "CONTENTS": {
            "PROPERTY": TEST_PROPERTY_ID,
            "ACTION": "GET",
            "VALUE": None
        }
    }

    EXPECTED_PROP_GET_RESPONSE = {
        'TOPICS': {
            'FROM': EMBEDDED_TEST_ID,
            'MSG_STATUS': 'OK',
            'MSG_TYPE': 'RESPONSE',
            'MSG_ID': MSG_ID_BASE+2,
            'TO': TEST_ITEM_ID,
            'RESPONSE_REQ': False,
            'TX_TYPE': 'DIRECT'
        },
        'CONTENTS': {
            'STATUS': 0,
            'ACTION': 'RESPONSE',
            'PROPERTY': TEST_PROPERTY_ID,
            'VALUE': 1
        }
    }

    PROPERTY_SET = {
        "TOPICS": {
            "TX_TYPE": "DIRECT",
            "MSG_TYPE": "PROPERTY",
            "TO": EMBEDDED_TEST_ID,
            "MSG_ID": MSG_ID_BASE+3,
            "FROM": TEST_ITEM_ID
        },
        "CONTENTS": {
            "PROPERTY": TEST_PROPERTY_ID,
            "ACTION": "SET",
            "VALUE": "1"
        }
    }

    EXPECTED_PROP_SET_RESPONSE = {
        'TOPICS': {
            'FROM': EMBEDDED_TEST_ID,
            'MSG_STATUS': 'OK',
            'MSG_TYPE': 'RESPONSE',
            'MSG_ID': MSG_ID_BASE+3,
            'TO': EMBEDDED_TEST_ID,
            'RESPONSE_REQ': False,
            'TX_TYPE': 'DIRECT'
        },
        'CONTENTS': {
            'STATUS': 0,
            'ACTION': 'RESPONSE',
            'PROPERTY': TEST_PROPERTY_ID
        }
    }

    def setUp(self):
        self.protocol = PCOM_Serial.open(adapter=self.adapter, port=self.PORT_NAME, baudrate=self.BAUD_RATE)
        self.protocol.get_discovery()


    def tearDown(self):
        PCOM_Serial._instance = None
        self.protocol.close()
        return

    @defer.inlineCallbacks
    def test_streaming(self):
        self.protocol.add_message_to_queue(self.STREAM_ON)
        msg = self.adapter.last_published
        self.assertEqual(msg, self.EXPECTED_RESPONSE)


    # @defer.inlineCallbacks
    # def test_property_get(self):
    #     self.protocol.add_message_to_queue(self.PROPERTY_GET)
    #     msg = yield self.adapter.published
    #     self.assertEqual(msg, self.EXPECTED_PROP_GET_RESPONSE)
    #
    # @defer.inlineCallbacks
    # def test_property_set(self):
    #     self.protocol.add_message_to_queue(self.PROPERTY_SET)
    #     msg = yield self.adapter.published
    #     self.assertEqual(msg, self.EXPECTED_PROP_SET_RESPONSE)



