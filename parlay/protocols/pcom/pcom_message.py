
from copy import deepcopy
from enums import MsgDataType, MsgType, MsgStatus, BaseCommands, ServiceIDs, is_valid_enum_value, name_from_enum
from parlay.protocols.utils import message_id_generator
import serial_encoding

OPTION_MASK = 0x0f
OPTION_SHIFT = 0

SUB_TYPE_MASK = 0x30
SUB_TYPE_SHIFT = 4

CATEGORY_MASK = 0xc0
CATEGORY_SHIFT = 6

class PCOMMessage(object):

    # maps the TO/FROm name to ints, and from ints back to names
    _lookup_map = {}
    #if we get a string, we need to assign a service ID. Start at 0xfc00 and go to 0xffff
    _lookup_id_generator = message_id_generator(0xffff, 0xfc00)

    VALID_MESSAGE_TYPES = ["COMMAND", "EVENT", "RESPONSE", "PROPERTY", "STREAM"]


    def __init__(self, to=None, from_=None, msg_id=0, tx_type=None, msg_type=None, attributes=None,
                 response_code=None, response_req=None, msg_status=None, contents=None, data=None, data_fmt=None):

        # TODO: Change response_req to response_code

        # private variables only accessed through @property functions

        self._msg_type = None
        self._to = None
        self._from_ = None
        self._tx_type = None
        self._response_req = None
        self._msg_status = None
        self._contents = None
        self._msg_subtype = None
        self._attributes = None
        self._format_string = ''
        self._data = []
        self._response_code = None


        self.to = to
        self.from_ = from_
        self.msg_id = msg_id
        self.tx_type = tx_type
        self.msg_type = msg_type
        self.response_req = response_req
        self.msg_status = msg_status
        self.contents = contents
        self.priority = 0
        self.format_string = data_fmt
        self.data = data
        self.response_code = response_code
        self.attributes = attributes

    @classmethod
    def _get_service_id(cls, name):
        """
        Gets a service ID from an item name
        """
        # if we're an int we're good
        if type(name) == int:
            return name

        if name in cls._lookup_map:
            return cls._lookup_map[name]

        else:
            service_id = cls._lookup_id_generator.next()
            cls._lookup_map[name] = service_id
            cls._lookup_map[service_id] = name
            return service_id

    @classmethod
    def _get_name_from_id(cls, service_id):
        """
        Gets a item name from an service ID
        """
        #if we need to look it up, look it up
        if service_id in cls._lookup_map:
            return cls._lookup_map[service_id]

        return service_id

    @classmethod
    def is_error(self):
        if MsgStatus.STATUS_ERROR_FIRST < self.status:
            return False
        else:
            return True

    @classmethod
    def from_dict_msg(cls, dict_msg):

        msg_id = dict_msg['TOPICS']['MSG_ID']

        to = cls._get_service_id(dict_msg['TOPICS']['TO'])
        from_ = cls._get_service_id(dict_msg['TOPICS']['FROM'])

        msg_type = dict_msg['TOPICS']['MSG_TYPE']

        response_req = dict_msg['TOPICS'].get("RESPONSE_REQ", False)

        msg_status = dict_msg['TOPICS'].get("MSG_STATUS", "INFO")
        tx_type = dict_msg['TOPICS'].get('TX_TYPE', "DIRECT")

        contents = dict_msg['CONTENTS']

        msg = cls(to=to, from_=from_, msg_id=msg_id, response_req=response_req, msg_type=msg_type,
                  msg_status=msg_status, tx_type=tx_type, contents=contents)

        return msg

    def _is_response_req(self):
        '''
        If the msg is an order a response is expected.
        TODO: Change '0' to constant for order.
        :return:
        '''

        return (self.msg_type & 0xf0) == serial_encoding.MessageType.Order

    def to_dict_msg(self):
        msg = {'TOPICS': {}, 'CONTENTS': {}}
        msg['TOPICS']['TO'] = self._get_name_from_id(self.to)
        msg['TOPICS']['FROM'] = self._get_name_from_id(self.from_)
        msg['TOPICS']['MSG_ID'] = self.msg_id
        msg['TOPICS']['RESPONSE_REQ'] = self._is_response_req()

        m_type = self.msg_type >> 4
        m_subtype = self.msg_type & 0x0f

        if m_type == serial_encoding.MessageType.Order:
            if m_subtype == serial_encoding.OrderSubTypes.Command:
                msg['TOPICS']['MSG_TYPE'] = "COMMAND"
                msg['CONTENTS']['COMMAND'] = self.response_req
            elif m_subtype == serial_encoding.OrderSubTypes.Get_Property:
                msg['TOPICS']['MSG_TYPE'] = "PROPERTY"
                msg['CONTENTS']['PROPERTY'] = self.response_req
                msg['CONTENTS']['ACTION'] = "GET"
            elif m_subtype == serial_encoding.OrderSubTypes.Set_Property:
                msg['TOPICS']['MSG_TYPE'] = "PROPERTY"
                msg['CONTENTS']['PROPERTY'] = self.response_req
                msg['CONTENTS']['ACTION'] = "SET"
            elif m_subtype == serial_encoding.OrderSubTypes.Stream_Property:
                msg['TOPICS']['MSG_TYPE'] = "STREAM"
                msg['CONTENTS']['STREAM'] = self.response_req
            elif m_subtype == serial_encoding.OrderSubTypes.Abort:
                raise Exception("Aborts aren't handled yet")
            else:
                raise Exception("Unhandled message subtype {}", m_subtype)

        elif m_type == serial_encoding.MessageType.Order_Response:
            msg['TOPICS']['MSG_TYPE'] = "RESPONSE"
            msg['CONTENTS']['STATUS'] = self.response_req
            if m_subtype == serial_encoding.OrderResponseSubTypes.OrderComplete:
                msg['TOPICS']["MSG_STATUS"] = "OK"
            elif m_subtype == serial_encoding.OrderResponseSubTypes.PropertyStream:
                raise Exception("Property streams aren't handled yet")
            elif m_subtype == serial_encoding.OrderResponseSubTypes.InProgress:
                raise Exception("In progress state not handled yet")
            elif m_subtype == serial_encoding.OrderResponseSubTypes.StateChange:
                raise Exception("State change unhandled")

        elif m_type == serial_encoding.MessageType.Notification:
            msg['TOPICS']["MSG_TYPE"] = "EVENT"
            msg['CONTENTS']['EVENT'] = self.response_req
            if m_subtype == serial_encoding.NotificationSubTypes.Error_Notice:
                msg['TOPICS']
            elif m_subtype == serial_encoding.NotificationSubTypes.Warning_Notice:
                raise Exception("Unhandled")
            elif m_subtype == serial_encoding.NotificationSubTypes.Data:
                raise Exception("Unhandled")


        return msg

    def category(self):
        return (self.msg_type & CATEGORY_MASK) >> CATEGORY_SHIFT

    def sub_type(self):
        return (self.msg_type & SUB_TYPE_MASK) >> SUB_TYPE_SHIFT

    def option(self):
        return (self.msg_type & OPTION_MASK) >> OPTION_SHIFT

    @property
    def to(self):
        return self._to

    @to.setter
    def to(self, value):
        if value is not None and not ServiceIDs.is_valid_service_id(value):
            raise ValueError("to {} is out of allowed range {} to {}".format(hex(value),
                                                                             hex(ServiceIDs.MIN_SERVICE_ID),
                                                                             hex(ServiceIDs.MAX_SERVICE_ID)))
        self._to = value

    @property
    def from_(self):
        return self._from_

    @from_.setter
    def from_(self, value):
        if value is not None and not ServiceIDs.is_valid_service_id(value):
            raise ValueError("from_ {} is out of allowed range {} to {}".format(hex(value),
                                                                                hex(ServiceIDs.MIN_SERVICE_ID),
                                                                                hex(ServiceIDs.MAX_SERVICE_ID)))
        self._from_ = value
    @property
    def msg_status(self):
        return self._msg_status

    @msg_status.setter
    def msg_status(self, value):
        self._msg_status = value

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if hasattr(value, '__iter__'):
            self._data = list(value)
        elif value == None:
            self._data = []
        else:
            self._data = [value]

    @property
    def format_string(self):
        return self._format_string

    @format_string.setter
    def format_string(self, value):
        # if value is a string, do a lookup for the int
        '''
         if isinstance(value, basestring) and hasattr(MsgDataType, value.upper()):
            value = getattr(MsgDataType, value.upper())
        # otherwise, if we're already an int
        elif not is_valid_enum_value(MsgDataType, value):
            raise ValueError("{} is not a valid option for MsgDataType".format(value))

            '''
        self._format_string = value

    @property
    def msg_type(self):
        return self._msg_type


    @msg_type.setter
    def msg_type(self, value):
        self._msg_type = value

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, value):
        self._event = None
        self._status = None
        self._command = value

    @property
    def response_code(self):
        return self._response_code

    @response_code.setter
    def response_code(self, value):
        self._response_code = value

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        self._event = value
        self._status = None
        self._command = None

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes = value
        if value is not None:
            self.priority = value & 0x01

    @property
    def status(self):
        return self._status


    @status.setter
    def status(self, value):
        self._event = None
        self._status = value
        self._command = None

    def get_command_event_status(self):
        if self._command is not None:
            return self._command
        elif self._status is not None:
            return self._status
        else:
            return self._event

    def set_command_event_status(self, val):
        if self._msg_type == MsgType.COMMAND:
            self.command = val
        elif self._msg_type == MsgType.COMMAND_RESPONSE:
            self.status = val
        elif self._msg_type == MsgType.SYSTEM_EVENT:
            self.event = val