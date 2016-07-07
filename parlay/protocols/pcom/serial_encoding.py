"""

Serial_encoding.py

A collection of helper functions that aid in the packing and unpacking of binary data as part
of the PCOM Serial Protocol.


"""

import struct
import array
import sys

from parlay.enum import enum

import pcom_message

FORMAT_STRING_TABLE = {

    'B':   1,
    'b':   1,
    'x':   1,
    'c':   1,
    'H':   2,
    'h':   2,
    'I':   4,
    'i':   4,
    'Q':   8,
    'q':   8,
    'f':   4,
    'd':   8,
    's':   1

}



MessagePriority = enum(
    'Normal',
    'High'
)

MessageType = enum(
    'Order',
    'Order_Response',
    'Notification'
)

OrderSubTypes = enum(
    'Command',
    'Get_Property',
    'Set_Property',
    'Stream_Property',
    'Abort'
)

OrderResponseSubTypes = enum(
    'OrderComplete',
    'PropertyStream',
    'InProgress',
    'StateChange'
)

NotificationSubTypes = enum(
    'Error_Notice',
    'Warning_Notice',
    'Data'
)

ResponseExpected = enum(
    'Yes',
    'No'
)

LoggingInfo = enum(
    'System Info',
    'Trace',
    'Debug',
    'Command Error',
    'Warning',
    'Error',
    'Critical Error')

CategoryMap = {
    'COMMAND': MessageType.Order,
    'PROPERTY': MessageType.Order,
    'RESPONSE': MessageType.Order_Response,
    'EVENT': MessageType.Notification
}

START_BYTE = 0x02
END_BYTE = 0x03
ESCAPE_BYTE = 0x10

START_BYTE_STR = b'\x02'
END_BYTE_STR  = b'\x03'
ESCAPE_BYTE_STR = b'\x10'

PACKET_TYPE_MASK = 0xf0
PACKET_SEQ_MASK = 0x0f
PACKET_HEADER_SIZE = 10

TYPE_ACK = 0x20
TYPE_NAK = 0x30
TYPE_NO_ACK_REQ = 0x40
TYPE_ACK_REQ = 0x80

SUBTYPE_MASK = 0x0f
TYPE_MASK = 0xf0

order_map = {0: "COMMAND", 1: "GET", 2: "SET", 3: "STREAM", 4: "ABORT"}

def deserialize_type(type_byte):

    '''

    Translates the serialized type byte to a JSON message type
    '''

    # TODO: Handle streams and other response sub types
    category = type_byte & 0xf0
    sub_type = type_byte & 0x0f

    msg_type = ""

    if category == MessageType.Order:
        if sub_type == OrderSubTypes.Command:
            msg_type = "COMMAND"
        else:
            msg_type = "PROPERTY"
    elif category == MessageType.Order_Response:
        msg_type = "RESPONSE"
    elif category == MessageType.Notification:
        msg_type = "EVENT"

    else:
        raise Exception("Unhandled type category")


    return msg_type

def deserialize_subtype(type_byte):
    serial_subtype = type_byte & SUBTYPE_MASK
    serial_msg_type = type_byte & TYPE_MASK
    r_subtype = None

    if serial_msg_type == MessageType.Order:
        r_subtype = order_map[serial_subtype]


def ack_nak_message(sequence_num, is_ack):
    """
    Generate an Ack message with the packets sequence number

    ------------------------------------------------------
    | ACK_MASK | Seq num, CHECKSUM, PAYLOAD SIZE (2 bytes)|
    ------------------------------------------------------
    """

    type_mask = TYPE_ACK if is_ack else TYPE_NAK
    return bytearray([sequence_num | type_mask, 0x100 - (sequence_num | type_mask), 0, 0])

def get_unpack_format(input_format, data):

    output_format = ""
    index = 0

    digit_str = ""
    for char in input_format:
        if char.isdigit():
            d
        else:
            output_format += char




def encode_pcom_message(msg):
    """
    Build the base binary message without the data sections
    :type msg: PCOMMessage
    """

    # Bytes [0:1]   Event ID (Unique ID of event)
    # Bytes [2:3]   Source ID
    # Bytes [4:5]   Destination ID
    # Bytes [6:7]   Order/response code (Command ID, property ID, or status code depending on event type)
    # Bytes [8]     Type (Type and subtype of event)
    # Bytes [9]     Attributes (Event attributes)
    # Bytes [10:N]  Format string (Null terminated data structure description (0 for no data))
    # Bytes [N+1:M] Data in the form of bytes[10:N]. Size must match format string

    payload = struct.pack("<HHHHBB", msg.msg_id, msg.from_, msg.to, serialize_response_code(msg), serialize_msg_type(msg),
                             serialize_msg_attrs(msg))

    if msg.format_string:
        payload += struct.pack("%ds" % len(msg.format_string), msg.format_string)

    # NULL terminate the format_string,
    # or if there isn't a format_string we just
    # want a NULL byte
    payload += struct.pack("B", 0)

    # If there is data to send, msg.format_string should not
    # contain anything. We want to add msg.data and a NULL byte
    # to the payload.
    if msg.data:
        msg.data = cast_data(msg.format_string, msg.data)
        payload += struct.pack(msg.format_string, *msg.data)

    return payload

def cast_data(fmt_string, data):
    result = []
    index = 0
    for i in fmt_string:
        if i.isalpha():
            if i in "bBhHiIlLqQnN":
                result.append(int(data[index]))
            elif i in "fd":
                result.append(float(data[index]))
            elif i is "s":
                pass
            else:
                raise Exception("Unhandled data type")

            index+=1


    return result



def serialize_msg_attrs(msg):
    '''

    :param msg: A Message object that was translated from a Parlay JSON message
    :return: A byte representing the attributes field of the byte sequence. This
    will be sent to the embedded core.

    '''
    return msg.priority | (msg.response_req < 1)

def serialize_response_code(message):
    '''

    :param msg_type: The message type of the dictionary message
    :return:
    '''

    m_type = message.msg_type
    code = None
    if m_type == 'COMMAND':
        code = message.contents.get('COMMAND', None)

    elif m_type == 'EVENT':
        code = message.contents.get('EVENT', None)

    elif m_type == 'STATUS' or m_type == 'RESPONSE':
        code = message.contents.get('STATUS', None)

    elif m_type == 'PROPERTY':
        code = message.contents.get('PROPERTY', None)

    return code

def serialize_msg_type(msg):

    '''
    Converts the message type to a binary sequence.

    :param msg:
    :return:
    '''

    cat = category(msg)
    sub_type = sub_category(msg, cat)

    return (cat << 4) | sub_type


def category(message):

    m_type = message.msg_type

    if m_type == 'COMMAND' or m_type == 'PROPERTY':
        return MessageType.Order
    elif m_type == 'EVENT':
        return MessageType.Notification
    elif m_type == 'RESPONSE':
        return MessageType.Order_Response
    else:
        raise Exception('Unhandled message type!')

def sub_category(msg, category):
    '''
    Extracts the subcategory from the parameter msg

    TODO: Clean this function up!
    '''

    # Possibly use dictionaries to map

    Notifications = {'ERROR' : 0, 'WARNING': 1, 'INFO': 2}
    Order_Responses = {'COMMAND': 0,
                       'PROPERTY': 0,
                       'STREAM': 1}

    type = msg.msg_type
    status = msg.msg_status
    if category == MessageType.Order:

        if type == 'COMMAND':

            return OrderSubTypes.Command

        elif type == 'PROPERTY':

            if msg.contents['ACTION'] == "SET":

                return OrderSubTypes.Set_Property

            elif msg.contents['ACTION'] == "GET":

                return OrderSubTypes.Get_Property

        elif type == 'STREAM':

                return OrderSubTypes.Stream

        # NOTE: Need to handle abort, not sure when
        # the abort subcategory should be used

    elif category == MessageType.Order_Response:

        if type == 'COMMAND' or type == 'PROPERTY':

            return OrderSubTypes.Order_Complete

        elif type == 'STREAM':

            return OrderSubTypes.Property_Stream

        elif status == 'PROGRESS':

            return OrderSubTypes.In_Progress

        # NOTE: Need to handle change state

    elif category == MessageType.Notification:

        return Notifications[status]





def decode_pcom_message(binary_msg):
    """
    Build a pcom message object from the serialized message
    :type binary_msg: str
    :return : PCOMMessage
    """
    msg_length = len(binary_msg)

    # ensure the packet is big enough
    if msg_length < PACKET_HEADER_SIZE:
        raise Exception('binary message less than minimum size', binary_msg)


    msg = pcom_message.PCOMMessage()

    # Unpack the header

    msg.msg_id, msg.from_, msg.to, msg.response_code, msg.msg_type, msg.attributes \
        = struct.unpack("<HHHHBB", binary_msg[0:PACKET_HEADER_SIZE])

    # Extract the format string
    format_string_end_index = str(binary_msg).find('\0', PACKET_HEADER_SIZE)
    format_string = binary_msg[PACKET_HEADER_SIZE:format_string_end_index+1]
    format_string_length = (format_string_end_index+1) - PACKET_HEADER_SIZE

    # If the format string only contains the NULL byte
    # our data and format_string should be empty
    if format_string_length == 1:
        msg.format_string = ''
        msg.data = []
        return msg

    # NOTE: There is a comma here because unpack returns a tuple
    msg.format_string, = struct.unpack("<%ds" % format_string_length, format_string)

    # The embedded serial message will have a format where string lengths are variable,
    # for example 'hSb'. The unpack() method requires string lengths to be specified, so we need
    # to translate the format string from the embedded message to something that unpack can understand like 'h12sb'
    receive_format = "<" + translate_fmt_str(msg.format_string, binary_msg[format_string_end_index+1:])

    #Strip NULL byte
    msg.format_string = msg.format_string[:-1]

    # NOTE: Struct unpack returns a tuple, which will be cast to a list
    # through msg.data's property function.
    # Each string in the data list will have a NULL byte attached to it.
    msg.data = struct.unpack(receive_format, binary_msg[format_string_end_index+1:])

    # Remove null byte from all strings in data
    print msg.data
    msg.data = map(lambda s: s[:-1] if isinstance(s, basestring) else s, msg.data)
    # It's possible to receive empty strings for parameter requests.
    # In the case that we do receive an empty string we should not store it in data
    msg.data = filter(lambda x: x != '', msg.data)
    print msg.data
    return msg

def get_str_len(bin_data):
    '''
    Helper function that gets the length of a binary sequence up to
    and including the NULL byte.

    :param bin_data: binary byte sequence
    :return: count (including NULL byte) of bytes
    '''

    count = 0
    for i in bin_data:
        if i is not '\x00':
            count += 1
        else:
            return count + 1 # Include NULL byte
    raise Exception("Data string wasn't NULL terminated")

def translate_fmt_str(fmt_str, bin_data):
    '''

    Given a format string used in the Embedded Core Protocol and a binary message
    returns a format string that may be used in the Python struct library.

    More specifically, the variable "s" format character is translated to
    "<str len>s".

    eg:

    translate_fmt_str("s", "\x65\x64\x00") --> "3s" because the length of the string is 3 (including NULL byte).

    :param fmt_str: A format string where 's' represents a variable length
    :param bin_data: Binary sequence of bytes where strings are NULL terminated
    :return: a new format string where 's' is replaced by '<len>s' where len is the length
    of the string represented by 's'.
    '''

    output_str = ""
    int_holder = ''
    index = 0

    for char in fmt_str:

        if char.isdigit():
            int_holder += char

        if char.isalpha():
            if char is 's':
                count = get_str_len(bin_data[index:])
                output_str += str(count)
            else:
                multiplier = 1 if len(int_holder) == 0 else int(int_holder)
                count = FORMAT_STRING_TABLE[char] * multiplier
                int_holder = ''

            index += count

        output_str += char

    return output_str

def pack_little_endian(type_string, list):
    a = array.array(type_string, list)
    if sys.byteorder != 'little':
        a.byteswap()

    return a


# TESTING PURPOSES

def hex_print(buf):
    print [hex(ord(x)) for x in buf]



def wrap_packet(packet, sequence_num, use_ack):
    """
    append book-end bytes, escape bytes that need escaping, and append serial level header info
    like sequence num and whetehr we need to ACK or not
    """

    # generate the packet header with the sequence number, length and ack
    # information

    NORMAL = 8
    ACK = 2
    checksum = 0

    payload_length = len(packet)
    sequence_byte = sequence_num | (NORMAL << 4) if use_ack else sequence_num | (ACK << 4)

    checksum_array = bytearray([sequence_byte])
    # calculate and add the checksum byte
    checksum_array.append(payload_length & 0xffff)
    checksum_array += packet

    checksum = (0x100 - checksum_calc(checksum_array)) & 0xff

    binary_msg = bytearray([sequence_byte, checksum]) + struct.pack("<H", payload_length & 0xffff) + packet

    #print 'BINARY MSG'
    #print  "--->", [hex(x) for x in binary_msg]

    # If the packet sum is not zero we should raise an exception
    # and not send the packet.
    if verify_packet(binary_msg):
        raise Exception("Checksum wasn't zero!")

    # Add the start stop and escape characters and send over serial port
    return _escape_packet(binary_msg)


def unstuff_packet(packet):
    """
    Unstuff the packet. Descape and return sequence number, ack_expected, is_ack, and is_nak, dict_msg as a tuple
    dict_msg is the message (if there is one) or None (if it's an ack/nak)
    """
    packet = _deescape_packet(packet)
    packet_len = len(packet)

    if verify_packet(packet) != 0:
        print "WARNING PACKET DIDNT ADD UP TO ZERO"

    if packet_len < 1:
        raise IndexError("Packets must be AT LEAST 3 bytes long. packet was: " + str(packet))

    # Read the UART packet header information
    sequence_num = packet[0] & PACKET_SEQ_MASK
    packet_type = (packet[0] & PACKET_TYPE_MASK)
    payload_length = packet[2] + packet[3]

    ack_expected = (packet_type == TYPE_ACK_REQ)
    is_ack = (packet_type == TYPE_ACK)
    is_nak = (packet_type == TYPE_NAK)

    data = packet[4: packet_len]

    dict_msg = None if (is_ack or is_nak) else decode_pcom_message(buffer(data))

    return sequence_num, ack_expected, is_ack, is_nak, dict_msg



def verify_packet(packet):
    '''
    Ensures that the packet's sum is zero.
    :param packet:
    :return:
    '''
    sum = 0
    for i in packet:
        sum += i

    return sum & 0xff

def _escape_packet(packet):
        """
        prepare the packet by adding the start (0x02) stop (0x03) and escape(0x10) characters
        Add escape char in front of  start, stop and escape
        """
        msg = bytearray()
        msg.append(START_BYTE) # START
        for b in packet:
            if b == START_BYTE or b == END_BYTE or b == ESCAPE_BYTE:   # if b is an escape values
                msg.append(ESCAPE_BYTE)
                msg.append(b + ESCAPE_BYTE)
            else:
                msg.append(b)
        msg.append(END_BYTE)
        return msg

def _deescape_packet(packet):
    result = bytearray()
    escaped = False
             #get rid of START and STOP byte
    for b in packet:
        if b == ESCAPE_BYTE:
            escaped = True  # next byte is escaped
        elif escaped:
            result.append(b - ESCAPE_BYTE)  # remove escaped addition
            escaped = False
        else:
            result.append(b)

    return result

def checksum_calc(msg):
        """Calculate the checksum for the given msg """
        checksum = 0
        for b in msg:
            checksum = (checksum + b) & 0xff
        return checksum



