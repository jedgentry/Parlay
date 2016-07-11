from parlay.enum import enum

CATEGORY_MASK = 0xc0
SUB_TYPE_MASK = 0x30
OPTION_MASK = 0xf0

CATEGORY_SHIFT = 6
SUB_TYPE_SHIFT = 4
OPTION_SHIFT = 0

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