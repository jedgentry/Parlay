
from copy import deepcopy
from enums import MsgDataType, MsgType, MsgStatus, BaseCommands, ServiceIDs, is_valid_enum_value, name_from_enum
from parlay.protocols.utils import message_id_generator

def system_id_from_service_id(service_id):
    if not ServiceIDs.is_valid_service_id(service_id):
        raise ValueError("Service id must be in range {} to {}".format(hex(ServiceIDs.MIN_SERVICE_ID),
                                                                       hex(ServiceIDs.MAX_SERVICE_ID)))
    return (service_id & ServiceIDs.SYSTEM_ID_MASK) >> ServiceIDs.SYSTEM_ID_SHIFT


class InvalidServiceMessageError(BaseException):
    pass

UI_SSCOM_ID = 0xf201


class ServiceMessage(object):

    # maps the TO/FROm name to ints, and from ints back to names
    _lookup_map = {}
    #if we get a string, we need to assign a service ID. Start at 0xfc00 and go to 0xffff
    _lookup_id_generator = message_id_generator(0xffff, 0xfc00)

    @staticmethod
    def _verify_command_status_event_for_msg_type(msg_type, command, status, event):
        if msg_type == MsgType.COMMAND and (status is not None or event is not None):
            raise ValueError("event and status arguments cannot be set if msg_type == MsgType.COMMAND")
        elif msg_type == MsgType.COMMAND_RESPONSE and (command is not None or event is not None):
            raise ValueError("event and command arguments cannot be set if msg_type == MsgType.COMMAND_RESPONSE")
        elif msg_type == MsgType.SYSTEM_EVENT and (status is not None or command is not None):
            raise ValueError("command and status arguments cannot be set if msg_type == MsgType.SYSTEM_EVENT")
        elif msg_type != MsgType.COMMAND and msg_type != MsgType.COMMAND_RESPONSE and msg_type != MsgType.SYSTEM_EVENT:
            if command is not None or status is not None or event is not None:
                raise ValueError("command, status, and event arguments cannot be set for msg_type {}".format(msg_type))

    @staticmethod
    def _verify_data(data):
        if not isinstance(data, list) and not isinstance(data, tuple):
            raise ValueError("data must be a list, tuple, or None")

    def __init__(self, to=None, from_=None, msg_id=0, tx_type=None, msg_type=None,
                 response_req=None, msg_status=None, contents=None):

        # private variables only accessed through @property functions

        self._msg_type = None
        self._to = None
        self._from_ = None
        self._tx_type = None
        self._response_req = None
        self._msg_status = None
        self._contents = None

        self.to = to
        self.from_ = from_
        self.msg_id = msg_id
        self.tx_type = tx_type
        self.msg_type = msg_type
        self.response_req = response_req
        self.msg_status = msg_status
        self.contents = contents
        self.priority = 0
        self.format_string = '\0'


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

        to = dict_msg['TOPICS']['TO']
        from_ = dict_msg['TOPICS']['FROM']

        msg_type = dict_msg['TOPICS']['MSG_TYPE']

        response_req = dict_msg['TOPICS']['RESPONSE_REQ']

        msg_status = dict_msg['TOPICS']['MSG_STATUS']
        tx_type = dict_msg['TOPICS']['TX_TYPE']

        contents = dict_msg['CONTENTS']

        msg = cls(to=to, from_=from_, msg_id=msg_id, response_req=response_req, msg_type=msg_type,
                  msg_status=msg_status, tx_type=tx_type, contents=contents)

        return msg


    def to_dict_msg(self):
        msg = {'TOPICS': {}, 'CONTENTS': {}}
        msg['TOPICS']['TO'] = self._get_name_from_id(self.to)
        msg['TOPICS']['FROM'] = self._get_name_from_id(self.from_)
        msg['TOPICS']['MSG_ID'] = self.msg_id
        msg['CONTENTS']['message_info'] = self.info

        msg['CONTENTS']['payload'] = {}
        msg['CONTENTS']['data_type'] = self.data_type
        name = name_from_enum(MsgDataType, self.data_type)
        if name is None:
            raise InvalidServiceMessageError("Invalid data type {}".format(self.data_type) +
                                             "Must be member of sscom.enums.MsgDataType.")
        msg['CONTENTS']['data_type_name'] = name

        self._verify_data(self.data)
        if (len(self.data) == 0 and self.data_type != MsgDataType.DATA_NONE) or \
           (len(self.data) > 0 and self.data_type == MsgDataType.DATA_NONE):
            raise InvalidServiceMessageError("data_type {} does not match data {}".format(self.data_type,
                                                                                          self.data))
        #msg['CONTENTS']['payload']['data'] = deepcopy(self.data)  # deep copy, just in case
        msg['CONTENTS']['data'] = deepcopy(self.data)
        self._verify_command_status_event_for_msg_type(self.msg_type, self.command, self.status, self.event)

        # translate a command to the parlay fields
        if self.msg_type in (MsgType.COMMAND, MsgType.ABORT, MsgType.RESET):
             msg['TOPICS']['MSG_TYPE']= 'COMMAND'
             if self.msg_type == MsgType.ABORT:
                 msg['CONTENTS']['COMMAND']= 'ABORT'
             elif self.msg_type== MsgType.RESET:
                  msg['CONTENTS']['COMMAND']= 'ABORT'
             else:
                if self.command is None:
                    raise InvalidServiceMessageError("command must be set for msg_type == MsgType.COMMAND")
             name = name_from_enum(BaseCommands, self.command)
             if name is not None:
                msg['CONTENTS']['COMMAND_NAME'] = name
             msg['CONTENTS']['COMMAND']= self.command

        # Translate the response to the Parlay type and status
        elif self.msg_type == MsgType.COMMAND_RESPONSE:
             msg['TOPICS']['MSG_TYPE'] = 'RESPONSE'
             if self.status == MsgStatus.STATUS_OKAY:
                msg['TOPICS']['MSG_STATUS'] = 'OK'
             elif self.status < MsgStatus.STATUS_WARNING_FIRST:
                msg['TOPICS']['MSG_STATUS'] = 'ACK'
             elif self.status < MsgStatus.STATUS_ERROR_FIRST:
                 msg['TOPICS']['MSG_STATUS'] = 'WARNING'
             else:
                 msg['TOPICS']['MSG_STATUS'] ='ERROR'
             name = name_from_enum(MsgStatus, self.status)
             if name is not None:
                msg['CONTENTS']['STATUS_NAME'] = name
             msg['CONTENTS']['STATUS']= self.status
             msg['CONTENTS']['RESULT'] = self.data

        # translate events
        elif self.msg_type in (MsgType.SYSTEM_EVENT, MsgType.STATE_RETURN, MsgType.LOG):
             msg['TOPICS']['MSG_TYPE'] = 'EVENT'
             msg['TOPICS']['MSG_STATUS'] = 'INFO'
             #TODO figure out async errors.
             msg['CONTENTS']['EVENT'] = self.status
        # translate data
        elif self.msg_type in (MsgType.RECV_DATA,MsgType.SEND_DATA):
             msg['TOPICS']['MSG_TYPE'] = 'DATA'

        # we don't know what to do with this
        else:
            raise InvalidServiceMessageError("Invalid message type {}. ".format(self.msg_type) +
                                             "Must be member of sscom.enums.MsgType.")


        # add our SSCOM info to the header
        msg['TOPICS']['message_type'] = self.msg_type
        name = name_from_enum(MsgType, self.msg_type)
        if name is not None:
            msg['TOPICS']['message_type_name'] = name.upper()

        return msg

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
        if value is None:
            self._data = []
        else:
            self._verify_data(value)
            self._data = value

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, value):
        # if value is a string, do a lookup for the int
        if isinstance(value, basestring) and hasattr(MsgDataType, value.upper()):
            value = getattr(MsgDataType, value.upper())
        # otherwise, if we're already an int
        elif not is_valid_enum_value(MsgDataType, value):
            raise ValueError("{} is not a valid option for MsgDataType".format(value))
        self._data_type = value

    @property
    def msg_type(self):
        return self._msg_type

    @msg_type.setter
    def msg_type(self, value):
        self._msg_type = value
        '''
        if value is not None:
            # if value is a string, do a lookup for the int
            if isinstance(value, basestring) and hasattr(MsgType, value.upper()):
                value = getattr(MsgType, value.upper())
            # otherwise, if we're already an int
            elif not is_valid_enum_value(MsgType, value):
                raise ValueError("{} is not a valid option for MsgType".format(value))
        self._msg_type = value
        if value == MsgType.COMMAND:
            self._event = None
            self._status = None
        elif value == MsgType.COMMAND_RESPONSE:
            self._command = None
            self._event = None
        elif value == MsgType.SYSTEM_EVENT:
            self._command = None
            self._status = None
        else:
            self._command = None
            self._status = None
            self._event = None
        '''

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, value):
        self._event = None
        self._status = None
        self._command = value

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, value):
        self._event = value
        self._status = None
        self._command = None

    @property
    def status(self):
        return self._status

    def response_req(self):
        return self.response_req

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

def service_msg_from_dict_msg(dict_msg):
    service_msg = ServiceMessage.from_dict_msg(dict_msg)
    return service_msg


def dict_msg_from_service_msg(service_msg):
    return service_msg.to_dict_msg()


class ResponseMessage(ServiceMessage):

    def __init__(self,
                 cmd_msg=None,
                 status=None,
                 info=0,
                 data=None, data_type=MsgDataType.DATA_NONE):
        to = None
        from_ = None
        msg_id = 0
        if cmd_msg is not None:
            to = cmd_msg.from_
            from_ = cmd_msg.to
            msg_id = cmd_msg.msg_id
        super(self.__class__, self).__init__(to=to, from_=from_, msg_id=msg_id, msg_type=MsgType.COMMAND_RESPONSE,
                                             status=status, info=info, data=data, data_type=data_type)
