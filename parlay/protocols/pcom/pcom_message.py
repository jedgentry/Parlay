"""

PCOM_Message.py

This is a message class that represents a middle ground between the high level JSON message and low level serial message.

Variables in this class will serve as storage points for the information inside of each message. The variables
are accessed using properties (@property and @setter decorators).

There are two key functions in this class (from_dict_msg() and to_dict_msg()) which handle the
conversion to and from a JSON message.

"""

from copy import deepcopy
from parlay.protocols.utils import message_id_generator
import serial_encoding
from enums import *

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
    def from_dict_msg(cls, dict_msg):

        """
        Converts a dictionary message to a PCOM message object

        :param dict_msg: JSON message
        :return: PCOM message object
        """

        msg_id = dict_msg['TOPICS']['MSG_ID']

        to = cls._get_service_id(dict_msg['TOPICS']['TO'])
        from_ = cls._get_service_id(dict_msg['TOPICS']['FROM'])

        msg_type = dict_msg['TOPICS']['MSG_TYPE']

        response_req = dict_msg['TOPICS'].get("RESPONSE_REQ", False)

        # msg_status = dict_msg['TOPICS'].get("MSG_STATUS", "INFO")

        msg_status = 0
        tx_type = dict_msg['TOPICS'].get('TX_TYPE', "DIRECT")

        contents = dict_msg['CONTENTS']


        msg = cls(to=to, from_=from_, msg_id=msg_id, response_req=response_req, msg_type=msg_type,
                  msg_status=msg_status, tx_type=tx_type, contents=contents)

        return msg

    def _is_response_req(self):
        '''
        If the msg is an order a response is expected.
        :return:
        '''

        return (self.category()) == MessageCategory.Order

    def _is_order(self):
        '''
        If the message is an order return True, if not return False
        :return:
        '''




    def to_dict_msg(self):
        msg = {'TOPICS': {}, 'CONTENTS': {}}
        msg['TOPICS']['TO'] = self._get_name_from_id(self.to)
        msg['TOPICS']['FROM'] = self._get_name_from_id(self.from_)
        msg['TOPICS']['MSG_ID'] = self.msg_id
        msg['TOPICS']['TX_TYPE'] = "DIRECT"

        if self.msg_status != STATUS_SUCCESS:
            msg['TOPICS']['MSG_TYPE'] = "RESPONSE"
            msg['CONTENTS']['STATUS'] = self.msg_status
            msg['TOPICS']['MSG_STATUS'] = "ERROR"
            msg['CONTENTS']['DESCRIPTION'] = STATUS_MAP[self.msg_status]
            msg['TOPICS']['RESPONSE_REQ'] = False
            return msg

        msg_category = self.category()
        msg_sub_type = self.sub_type()
        msg_option = self.option()

        msg['TOPICS']['RESPONSE_REQ'] = self._is_response_req()


        if msg_category == MessageCategory.Order:
            if msg_sub_type == OrderSubType.Command:
                if msg_option == OrderCommandOption.Normal:
                    msg['TOPICS']['MSG_TYPE'] = "COMMAND"
                    msg['CONTENTS']['COMMAND'] = self.response_code
            elif msg_sub_type == OrderSubType.Property:
                if msg_option == OrderPropertyOption.Get_Property:
                    msg['TOPICS']['MSG_TYPE'] == "PROPERTY"
                    msg['CONTENTS']['PROPERTY'] = self.response_code
                    msg['CONTENTS']['ACTION'] = "GET"
                elif msg_option == OrderPropertyOption.Set_Property:
                    msg['TOPICS']['MSG_TYPE'] == "PROPERTY"
                    msg['CONTENTS']['PROPERTY'] = self.response_code
                    msg['CONTENTS']['ACTION'] = "SET"
                    msg['CONTENTS']['VALUE'] = self.data[0] # TODO: Support no data
                elif msg_option == OrderPropertyOption.Stream_On:
                    raise Exception("Stream on not handled yet")
                elif msg_option == OrderPropertyOption.Stream_Off:
                    raise Exception("Stream off not handled yet")

            else:
                raise Exception("Unhandled message subtype {}", msg_sub_type)

        elif msg_category == MessageCategory.Order_Response:
            msg['TOPICS']['MSG_TYPE'] = "RESPONSE"
            msg['CONTENTS']['STATUS'] = self.msg_status
            if msg_sub_type == ResponseSubType.Command:
                msg['TOPICS']['MSG_STATUS'] = "OK"
                if msg_option == ResponseCommandOption.Complete:
                    item = command_map.get(self.from_, None)
                    if item:
                        msg['CONTENTS']['RESULT'] = self._get_result_string(item[self.response_code].output_names, self.data) # Maybe need to change to tuple or something
                    else:
                        msg['CONTENTS']['RESULT'] = {}
                elif msg_option == ResponseCommandOption.Inprogress:
                    raise Exception("Inprogress not supported yet")
            elif msg_sub_type == ResponseSubType.Property:
                msg['TOPICS']['MSG_STATUS'] = "OK"
                if msg_option == ResponsePropertyOption.Get_Response:
                    msg['CONTENTS']['ACTION'] = "RESPONSE"
                    msg['CONTENTS']['PROPERTY'] = self.response_code  # TODO
                    msg['CONTENTS']['VALUE'] = self.data[0] # TODO: support empty data
                elif msg_option == ResponsePropertyOption.Set_Response:
                    msg['CONTENTS']['ACTION'] = "RESPONSE"
                    msg['CONTENTS']['PROPERTY'] = self.response_code  # TODO
                    pass # NOTE: set responses do not have a 'value' field
                elif msg_option == ResponsePropertyOption.Stream_Response:
                    msg['TOPICS']['MSG_TYPE'] = "STREAM"
                    msg['TOPICS']['STREAM'] = self.response_code
                    msg['CONTENTS']['VALUE'] = self.data[0]
                    msg['CONTENTS']['RATE'] = 1000

        elif msg_category == MessageCategory.Notification:
            msg['TOPICS']["MSG_TYPE"] = "EVENT"
            msg['CONTENTS']['EVENT'] = self.response_req


        return msg

    def _get_result_string(self, output_param_names, data_list):
        """
        Given the output names of a command and a data list, returns a dictionary of output_names -> data

        :param output_param_names: The output names of a command found during discovery
        :param data_list: The data passed to the protocol from the command
        :return: a dictionary of output names mapped to their data segments
        """

        # If the first output parameter is a list then simply return
        # a all of the data
        if len(output_param_names) > 0 and  output_param_names[0][-2:] == "[]":
            return {output_param_names[0]: self.data}
        # Otherwise return a map of output names -> data
        else:
            return dict(zip(output_param_names, self.data))

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
        self._to = value

    @property
    def from_(self):
        return self._from_

    @from_.setter
    def from_(self, value):
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
    def msg_status(self):
        return self._msg_status


    @msg_status.setter
    def msg_status(self, value):
        self._msg_status = value
