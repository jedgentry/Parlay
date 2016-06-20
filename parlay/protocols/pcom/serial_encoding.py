"""
The serial_encoding module is a collection of helper methods and lookups for the SSCOM binary serial protocol.
"""

import struct
import array
import sys

from parlay.enum import enum

import service_message


ServiceMessageType = enum(
    "Command",
    "Redirected Command",
    "Command Response",
    "Send Data",
    "Receive Data",
    "Reset",
    "Abort",
    "Timer",
    "System Event",
    "State Return Type",
    "Log Type"
)

BufferDataType = enum(
    'DATA_NONE',
    'DATA_8',
    'DATA_8S',
    'DATA_16',
    'DATA_16S',
    'DATA_32',
    'DATA_32S',
    'DATA_64',
    'DATA_64S',
    'DATA_FLOAT',
    'DATA_DOUBLE',
    'DATA_ASCII',
    'DATA_UNICODE',
    'DATA_COM_SVC_MSG',
    'DATA_STR',
    'DATA_FLEX_TYPE',
    #not an enum type, just the total size of the enum
    'DATA_TYPE_MAX'
)

#Lookup table from our ENUM to pack string
#call this with the list of values, and you'll get a buffer back that has been packed
#in binary form
BufferDataCTypePack = [lambda data: bytearray()] * BufferDataType.DATA_TYPE_MAX
BufferDataCTypePack[BufferDataType.DATA_NONE]       = lambda data: bytearray()
BufferDataCTypePack[BufferDataType.DATA_8]          = lambda data: pack_little_endian('B', data)
BufferDataCTypePack[BufferDataType.DATA_8S]         = lambda data: pack_little_endian('b', data)
BufferDataCTypePack[BufferDataType.DATA_16]         = lambda data: pack_little_endian('H', data)
BufferDataCTypePack[BufferDataType.DATA_16S]        = lambda data: pack_little_endian('h', data)
BufferDataCTypePack[BufferDataType.DATA_32]         = lambda data: pack_little_endian('I', data)
BufferDataCTypePack[BufferDataType.DATA_32S]        = lambda data: pack_little_endian('i', data)
BufferDataCTypePack[BufferDataType.DATA_64]         = lambda data: pack_little_endian('Q', data)
BufferDataCTypePack[BufferDataType.DATA_64S]        = lambda data: pack_little_endian('q', data)
BufferDataCTypePack[BufferDataType.DATA_FLOAT]      = lambda data: pack_little_endian('f', data)
BufferDataCTypePack[BufferDataType.DATA_DOUBLE]     = lambda data: pack_little_endian('d', data)
BufferDataCTypePack[BufferDataType.DATA_ASCII]      = lambda data: bytearray(data[0], encoding="ascii")
BufferDataCTypePack[BufferDataType.DATA_UNICODE]    = lambda data: bytearray(data[0], encoding="utf8")
BufferDataCTypePack[BufferDataType.DATA_COM_SVC_MSG]= lambda data : pack_svc_msg(data)
#Turn it into a list of NULL terminaed strings
BufferDataCTypePack[BufferDataType.DATA_STR]        = lambda data: bytearray(chr(0x0).join(data) + chr(0x0))


#lookup for data sizes per units in bytes (needed for FLEX messages)
BufferDataTypeByteSize = [1] * BufferDataType.DATA_TYPE_MAX
BufferDataTypeByteSize[BufferDataType.DATA_8]          = 1
BufferDataTypeByteSize[BufferDataType.DATA_8S]         = 1
BufferDataTypeByteSize[BufferDataType.DATA_16]         = 2
BufferDataTypeByteSize[BufferDataType.DATA_16S]        = 2
BufferDataTypeByteSize[BufferDataType.DATA_32]         = 4
BufferDataTypeByteSize[BufferDataType.DATA_32S]        = 4
BufferDataTypeByteSize[BufferDataType.DATA_64]         = 8
BufferDataTypeByteSize[BufferDataType.DATA_64S]        = 8
BufferDataTypeByteSize[BufferDataType.DATA_FLOAT]      = 4
BufferDataTypeByteSize[BufferDataType.DATA_DOUBLE]     = 8
BufferDataTypeByteSize[BufferDataType.DATA_ASCII]      = 1
BufferDataTypeByteSize[BufferDataType.DATA_UNICODE]    = 1

BufferDataTypeByteSize[BufferDataType.DATA_STR]        = 1


#Lookup table from our ENUM to UNpack string
#call this with the list of values, and you'll get a buffer back that has been packed
#in binary form
BufferDataCTypeUnpack = [lambda data: data] * BufferDataType.DATA_TYPE_MAX
BufferDataCTypeUnpack[BufferDataType.DATA_NONE]       = lambda data: None
BufferDataCTypeUnpack[BufferDataType.DATA_8]          = lambda data: struct.unpack('<' + 'B' * len(data), data)
BufferDataCTypeUnpack[BufferDataType.DATA_8S]         = lambda data: struct.unpack('<' + 'b' * len(data), data)
BufferDataCTypeUnpack[BufferDataType.DATA_16]         = lambda data: struct.unpack('<' + 'H' * (len(data)/2), data)
BufferDataCTypeUnpack[BufferDataType.DATA_16S]        = lambda data: struct.unpack('<' + 'h' * (len(data)/2), data)
BufferDataCTypeUnpack[BufferDataType.DATA_32]         = lambda data: struct.unpack('<' + 'I' * (len(data)/4), data)
BufferDataCTypeUnpack[BufferDataType.DATA_32S]        = lambda data: struct.unpack('<' + 'i' * (len(data)/4), data)
BufferDataCTypeUnpack[BufferDataType.DATA_64]         = lambda data: struct.unpack('<' + 'Q' * (len(data)/8), data)
BufferDataCTypeUnpack[BufferDataType.DATA_64S]        = lambda data: struct.unpack('<' + 'q' * (len(data)/8), data)
BufferDataCTypeUnpack[BufferDataType.DATA_FLOAT]      = lambda data: struct.unpack('<' + 'f' * (len(data)/4), data)
BufferDataCTypeUnpack[BufferDataType.DATA_DOUBLE]     = lambda data: struct.unpack('<' + 'd' * (len(data)/8), data)
BufferDataCTypeUnpack[BufferDataType.DATA_ASCII]      = lambda data: [data]
BufferDataCTypeUnpack[BufferDataType.DATA_UNICODE]    = lambda data: [data]
BufferDataCTypeUnpack[BufferDataType.DATA_COM_SVC_MSG]= lambda data: [data]
#Turn from a list of NULL terminated strings
BufferDataCTypeUnpack[BufferDataType.DATA_STR]        = lambda data: data.split(chr(0x0))
BufferDataCTypeUnpack[BufferDataType.DATA_FLEX_TYPE]  = lambda data: _decode_flex_type(data)



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
    'Order Complete',
    'Property Stream',
    'In Progress',
    'State change'
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

START_BYTE = 0x02
STOP_BYTE  = 0x03
ESCAPE_BYTE = 0x10

START_BYTE_STR = b'\x02'
STOP_BYTE_STR  = b'\x03'
ESCAPE_BYTE_STR = b'\x10'

def ack_nak_message(sequence_num, is_ack):
    """
    Generate an Ack message with the packets sequence number
    """
    ack_nak_bit_mask = 0x80 if is_ack else  0x40
    return bytearray([sequence_num | ack_nak_bit_mask, 0, 0x100 - (sequence_num | ack_nak_bit_mask)])


def encode_service_message(msg):
    """
    Build the base binary message without the data sections
    :type msg: service_msg.ServiceMessage
    """

    # Bytes [0:1]   Event ID (Unique ID of event)
    # Bytes [2:3]   Source ID
    # Bytes [4:5]   Destination ID
    # Bytes [6:7]   Order/response code (Command ID, property ID, or status code depending on event type)
    # Bytes [8]     Type (Type and subtype of event)
    # Bytes [9]     Attributes (Event attributes)
    # Bytes [10:N]  Format string (Null terminated data structure description (0 for no data))
    # Bytes [N+1:M] Data in the form of bytes[10:N]. Size must match format string

    '''
    Do I need this??

    #cast all to ints in case they didn't get decoded that way
    topIService, bottomIService = 0xffff, 0xffff                 # to/from device codes
    #command, status, event are all the same to us
    command = msg.get_command_event_status()
    #pack them up in a binary buffer

  #  binary_msg = struct.pack("<HHHHHHI", msg.msg_id, msg.from_, msg.to, msg.response_code, msg.msg_type, msg.attributes, msg.format_string)

    '''

    binary_msg = struct.pack("<HHHHBBs", msg.msg_id, msg.from_, msg.to, response_code(msg), serialize_msg_type(msg),
                             serialize_msg_attrs(msg) , msg.format_string)

    '''

    Not sure if I need this stuff yet.


    message_type = msg.msg_type

    data_type = msg.data_type
    if isinstance(data_type, basestring):
        data_type = getattr(BufferDataType, data_type)

    binary_msg += struct.pack("<B", (message_type & 0xF) | ((data_type & 0xF) << 4))

    # Byte 18    Attributes:
    #   Bits 0-1  Priority  0= normal, 1 = drop-able,  2 = high
    #   Bits 2:4  Logging Info
    message_priority = MessagePriority.Normal
    binary_msg += struct.pack("<B", (message_priority & 0x3) | ((message_logging & 0x7) << 2))


    if len(msg.data) > 0:
        binary_msg += BufferDataCTypePack[data_type]([x for x in msg.data if x != '' and x is not None]).tostring()
    '''
    return binary_msg

def serialize_msg_attrs(msg):
    '''

    :param msg: A Message object that was translated from a Parlay JSON message
    :return: A byte representing the attributes field of the byte sequence. This
    will be sent to the embedded core.

    '''
    return msg.priority | (msg.response_req < 1)

def response_code(message):
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

    print m_type

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





def decode_service_message(binary_msg):
    """
    Build the json message from the binary version
    :type binary_msg: str
    """
    length = len(binary_msg)

    # ensure the packet is big enough
    if length < 18:
        raise Exception('binary message less than minimum size', binary_msg)


    msg = service_message.ServiceMessage()
    # create the json message with the basic information
    msg.to, msg.from_, topIService, bottomIService, command, msg.msg_id, msg.info = struct.unpack("<HHHHHHI", binary_msg[0:16])
    msg.data_type = (ord(binary_msg[16]) >> 4)

    msg.msg_type = (ord(binary_msg[16]) & 0xF)
    msg.set_command_event_status(command)  # set the command/status/event based on the type
    #message_logging = LoggingInfo.lookup[((ord(binary_msg[17]) >> 2) & 0x7)],
    #message_priority= MessagePriority.lookup[(ord(binary_msg[17]) & 0x3)],

    # decode the data buffer if there is one
    if length > 18:
        try:
            msg.data = BufferDataCTypeUnpack[msg.data_type](binary_msg[18:])
        except IndexError:
            print msg.data_type, " Type not found"
            raise Exception('data type lookup not found', msg.data_type)
    else:
        msg.data = []

    return msg


def pack_little_endian(type_string, list):
    a = array.array(type_string, list)
    if sys.byteorder != 'little':
        a.byteswap()

    return a


def pack_svc_msg(data):
    #TODO: pack entire service messages into payload.
    return data
    #raise NotImplementedError()

def pack_flex_data(data):
    #TODO: Do we need to pack flex data?
    raise NotImplementedError()


def stuff_packet(packet, sequence_num, use_ack):
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
    sequence_byte = sequence_num + (NORMAL << 4)

    if use_ack:
        sequence_byte |= 0x10  # 0x10 = needs an ACK flag

    checksum_array = bytearray([sequence_byte])
    # calculate and add the checksum byte
    print "CHECKSUM = " + str(checksum)
    print "PAYLOAD SIZE = " + str(payload_length)
    checksum_array.append(payload_length & 0xffff)
    checksum_array += packet

    checksum = 0x100 - checksum_calc(checksum_array)

    binary_msg = bytearray([sequence_byte, checksum]) + struct.pack("<H", payload_length & 0xffff) + packet
    print 'BINARY MSG'
    print  "--->", [hex(x) for x in binary_msg]
    # add the start stop and escape characters and send over serial port
    return _escape_packet(binary_msg)


def unstuff_packet(packet):
    """
    Unstuff the packet. Descape and  return sequence number, ack_expected, is_ack, and is_nak, dict_msg as a tuple
    dict_msg is the message (if there is one) or None (if it's an ack/nak)
    """
    packet = _deescape_packet(packet)
    packet_len = len(packet)
    if packet_len < 1:
        raise IndexError("Packets must be AT LEAST 3 bytes long. packet was: " + str(packet))

    # read the header information for this packet
    sequence_num = packet[0] & 0x0f
    ack_expected = (packet[0] & 0x10) == 0x10
    payload_length = packet[1] + ((packet[0] & 0xC0) << 2)

    #we're an ACK or a nack
    if packet_len == 3:
        is_ack = (packet[0] & 0x80) == 0x80
        return sequence_num, False, is_ack, not is_ack, None
    else:
        data = packet[2: packet_len - 1]
        return sequence_num, ack_expected, False, False, decode_service_message(buffer(data))




def _escape_packet(packet):
        """
        prepare the packet by adding the start (0x02) stop (0x03) and escape(0x10) characters
        Add escape char in front of  start, stop and escape
        """
        msg = bytearray()
        msg.append(START_BYTE) # START
        for b in packet:
            if b == START_BYTE or b == STOP_BYTE or b == ESCAPE_BYTE:   # if b is an escape values
                msg.append(ESCAPE_BYTE)
                msg.append(b + ESCAPE_BYTE)
            else:
                msg.append(b)
        msg.append(STOP_BYTE)
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




def _decode_flex_type(data):
    header_data, payload = data.split(b'\x00', 1)
    header_data = bytearray(header_data)
    headers = []  # python struct string for .unpack
    for h in header_data:
        data_type = h & 0xF
        num_elements = (h >> 4) & 0xF
        headers.append((data_type, num_elements))

    result = []

    for h in headers:
        if h[0] == BufferDataType.DATA_STR:  # if it's a string we need to count the # of \0s
            split = payload.split(b'\x00', h[1])  # split up to n \0s
            payload = split[-1]  # last index is rest of string
            result.extend(split[:-1])
        else:
            size = BufferDataTypeByteSize[h[0]] * h[1]  # byte size * num_elements
            chunk = payload[0:size]
            payload = payload[size:]
            result.extend(BufferDataCTypeUnpack[h[0]](chunk))

    return result


if __name__ == "__main__":
    import json
    import serial
    #msg = msg = {'to': 0, 'from': 0, 'command': 0x32, 'message_id': 100, 'message_info': 0,
    #    'payload': {"type": "DATA_8S", 'data': [-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10]},
    #    'message_type': "Command" }

    msg = msg = {'to': 0, 'from': 65280, 'command': 0x32, 'message_id': 100, 'message_info': 0,
        'message_type': "Command" }
    print "Msg:", msg
    binary_msg = encode_service_message(msg)


    s = serial.Serial("/dev/ttyUSB0", baudrate=57600, timeout=1)
    print "Binary: ", [hex(ord(x)) for x in binary_msg]
    binary_msg = stuff_packet(binary_msg, 1, True)
    print "Stuffed: ", [hex(x) for x in binary_msg]
    print "Unstuffed: ", unstuff_packet(binary_msg)[4]
    s.write(binary_msg)

    resp = s.read(size=200)
    print "resp", [hex(ord(s)) for s in resp]

    #dict_msg = decode_service_message(buffer(unstuff_packet(binary_msg)[4]))
    #print "Dict: ", dict_msg



