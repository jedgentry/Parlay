from pcom_message import PCOMMessage
import struct
import serial_encoding
import unittest
from pcom_serial import PCOM_Serial
from parlay.server.broker import Broker

class TestSerialEncoding(unittest.TestCase):

    b_msg_id = 20
    b_source_id = 5
    b_destination_id = 7
    b_order_code = 1001
    b_type = "COMMAND"
    b_attributes = 0x01
    b_format_string = ''
    b_incoming_data = []

    b_contents = {"COMMAND": 1001}
    s = PCOMMessage(msg_id=b_msg_id, from_=b_source_id, to= b_destination_id,
                       response_code=b_order_code, msg_type=b_type, attributes=b_attributes,
                       data_fmt=b_format_string, data=b_incoming_data, contents=b_contents)


    def test_binary_unpacking(self):

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

    def test_message_passing(self):
        self.broker = Broker.get_instance()
        self.protocol = PCOM_Serial.open(broker=self.broker, port="/dev/cu.usbserial-FTHM129F", baudrate=57600)
        self.protocol._send_message_down_transport(self.command_msg)






class TestMessagePassing:
    def test_commands(self):
        pass
    def test_get_properties(self):
        pass
    def test_set_properties(self):
        pass


if __name__ == '__main__':
    unittest.main()
