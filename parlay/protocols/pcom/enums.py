from parlay.enum import enum

CATEGORY_MASK = 0xc0
SUB_TYPE_MASK = 0x30
OPTION_MASK = 0xf0

CATEGORY_SHIFT = 6
SUB_TYPE_SHIFT = 4
OPTION_SHIFT = 0


GET_SUBSYSTEMS = 0
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