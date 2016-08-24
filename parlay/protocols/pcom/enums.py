from parlay.enum import enum


# Store a map of Item IDs -> Command ID -> Command Objects
# Command objects will store the parameter -> format mapping
command_map = {}

# Store a map of properties. We must keep track of a
# name -> format mapping in order to serialize data
property_map = {}

# NOTE: These are global because the serial_encoding.py and
# pcom_message.py modules need access to them. Since they will
# be large maps we do not want to pass them as parameters.

GET_SUBSYSTEMS = 0
RESET_ITEM = 1000
GET_ITEM_NAME = 1001
GET_ITEM_TYPE = 1002
GET_COMMAND_IDS = 1003
GET_PROPERTY_IDS = 1004
GET_COMMAND_NAME = 1010
GET_COMMAND_INPUT_PARAM_FORMAT = 1011
GET_COMMAND_INPUT_PARAM_NAMES = 1012
GET_COMMAND_OUTPUT_PARAM_DESC = 1013
GET_PROPERTY_NAME = 1020
GET_PROPERTY_TYPE = 1021

DISCOVERY_MESSAGES = [GET_ITEM_NAME, GET_ITEM_TYPE, GET_COMMAND_IDS, GET_PROPERTY_IDS, GET_COMMAND_NAME,
                      GET_COMMAND_INPUT_PARAM_FORMAT, GET_COMMAND_INPUT_PARAM_NAMES, GET_COMMAND_OUTPUT_PARAM_DESC,
                      GET_PROPERTY_NAME, GET_PROPERTY_TYPE, GET_SUBSYSTEMS, RESET_ITEM]



ITEM_TYPE_HIDDEN = 1000
# From serial_encoding.py

START_BYTE = 0x02
END_BYTE = 0x03
ESCAPE_BYTE = 0x10

STATUS_SUCCESS = 0
STATUS_ERROR = 1

START_BYTE_STR = b'\x02'
END_BYTE_STR  = b'\x03'
ESCAPE_BYTE_STR = b'\x10'

PACKET_TYPE_MASK = 0xf0
PACKET_SEQ_MASK = 0x0f
PACKET_HEADER_SIZE = 12

TYPE_ACK = 0x20
TYPE_NAK = 0x30
TYPE_NO_ACK_REQ = 0x40
TYPE_ACK_REQ = 0x80

# From pcom_message.py

OPTION_MASK = 0x0f
OPTION_SHIFT = 0

SUB_TYPE_MASK = 0x30
SUB_TYPE_SHIFT = 4

CATEGORY_MASK = 0xc0
CATEGORY_SHIFT = 6


ORDER_TYPES = ["COMMAND", "PROPERTY", "STREAM"]
NOTIFICATION_TYPES = ["EVENT"]
RESPONSE_TYPES = ["RESPONSE"]
MessageCategory = enum(
    'Order',
    'Order_Response',
    'Notification'
)

OrderSubType = enum(
    'Command',
    'Property'
)

ResponseSubType = enum(
    'Command',
    'Property'
)

NotificationSubType = enum(
    'Info'
)

OrderCommandOption = enum(
    'Normal',
    'Special'
)

OrderPropertyOption = enum(
    'Get_Property',
    'Set_Property',
    'Stream_On',
    'Stream_Off'
)

ResponseCommandOption = enum(
    'Complete',
    'Inprogress'
)

ResponsePropertyOption = enum(
    'Get_Response',
    'Set_Response',
    'Stream_Response'
)

NotificationOptions = enum(
    'Error',
    'Warning',
    'Info',
    'Debug'
)


PSTATUS_SUCCESS = 0
PSTATUS_COMMAND_NOT_SUPPORTED = 1000
PSTATUS_NOT_INITIALIZED = 1001
PSTATUS_OVERRUN = 1005
PSTATUS_TIMEOUT = 1006
PSTATUS_NOT_FOUND = 1007
PSTATUS_NOT_IMPLEMENTED = 1008
PSTATUS_INVALID_ITEM = 1010
PSTATUS_INVALID_PARAMETER = 1011
PSTATUS_INVALID_EVENT_TYPE = 1012
PSTATUS_INVALID_POINTER = 1013
PSTATUS_INVALID_SIZE = 1014
PSTATUS_INVALID_DATA = 1015
PSTATUS_INVALID_STATE = 1016
PSTATUS_INVALID_COMMAND = 1017
PSTATUS_OS_INIT_ERROR = 1020
PSTATUS_OS_ERROR = 1021
PSTATUS_PROPERTY_NOT_SUPPORTED = 1030
PSTATUS_PROPERTY_NOT_WRITABLE = 1031
PSTATUS_STREAM_NOT_SUPPORTED = 1032
PSTATUS_ENCODING_ERROR = 1033


# Maps status code to their corresponding description.
STATUS_MAP = {
    PSTATUS_SUCCESS: "Command successful",
    PSTATUS_COMMAND_NOT_SUPPORTED: "Command is not supported",
    PSTATUS_NOT_INITIALIZED: "PSTATUS_NOT_INITIALIZED",
    PSTATUS_OVERRUN: "PSTATUS_OVERRUN",
    PSTATUS_TIMEOUT: "PSTATUS_TIMEOUT",
    PSTATUS_NOT_FOUND: "PSTATUS_NOT_FOUND",
    PSTATUS_NOT_IMPLEMENTED: "PSTATUS_NOT_IMPLEMENTED",
    PSTATUS_INVALID_ITEM: "PSTATUS_INVALID_ITEM",
    PSTATUS_INVALID_PARAMETER: "Invalid parameter provided. Data type and size must match those in the item declaration.",
    PSTATUS_INVALID_EVENT_TYPE: "PSTATUS_INVALID_EVENT_TYPE",
    PSTATUS_INVALID_POINTER: "PSTATUS_INVALID_POINTER",
    PSTATUS_INVALID_SIZE: "PSTATUS_INVALID_SIZE",
    PSTATUS_INVALID_DATA: "PSTATUS_INVALID_DATA",
    PSTATUS_INVALID_STATE: "PSTATUS_INVALID_STATE",
    PSTATUS_INVALID_COMMAND: "PSTATUS_INVALID_COMMAND",
    PSTATUS_OS_INIT_ERROR: "PSTATUS_OS_INIT_ERROR",
    PSTATUS_OS_ERROR: "PSTATUS_OS_ERROR",
    PSTATUS_PROPERTY_NOT_SUPPORTED: "PSTATUS_PROPERTY_NOT_SUPPORTED",
    PSTATUS_PROPERTY_NOT_WRITABLE: "Error: property is not writable",
    PSTATUS_STREAM_NOT_SUPPORTED: "PSTATUS_STREAM_NOT_SUPPORTED",
    PSTATUS_ENCODING_ERROR: "Could not translate the packet to a serial counterpart."
                             " This is most likely because the data format of"
                             " the parameters did not match the data types provided by the user. "
                             "For example, if the parameter requires an integer and a string was entered."
}