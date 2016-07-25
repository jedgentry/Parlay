"""

pcom_serial.py

This protocol enables Parlay to interact with embedded devices. This class handles the passing of messages
between Parlay and embedded devices.


"""

from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from twisted.internet import defer

from parlay.items.parlay_standard import ParlayStandardItem, INPUT_TYPES
from parlay.protocols.base_protocol import BaseProtocol
from parlay.protocols.utils import message_id_generator, timeout, MessageQueue, TimeoutError, delay

from serial.tools import list_ports

from serial_encoding import *
from enums import *

from collections import namedtuple


# A namedtuple representing the information of each property.
# This information will be retrieved during discovery.
# name = string representing the name of the property
# format = format describing the type of property.
# Eg. If the property were a floating point value it would be 'f'

PropertyData = namedtuple('PropertyData', 'name format')


class PCOMSerial(BaseProtocol, LineReceiver):

    # Constant number of retries before another message is sent out
    # after not receiving an ACK
    NUM_RETRIES = 3

    # The item ID of the protocol during discovery.
    DISCOVERY_CODE = 0xfefe

    # The minimum event ID. Some event IDs may need to be reserved
    # in the future.
    MIN_EVENT_ID = 0

    # The number of bits reserved for the event ID in the serialized
    # event protocol. Eg. if two bytes are reserved this number should be 16.
    NUM_EVENT_ID_BITS = 16

    # Item ID of the embedded reactor
    EMBD_REACTOR_ID = 0
    BROADCAST_SUBSYSTEM_ID = 0x8000
    SUBSYSTEM_SHIFT = 8

    # Number of bits we have for sequence number
    SEQ_BITS = 4

    @classmethod
    def open(cls, adapter, port, baudrate):
        """
        :param cls: The class object
        :param adapter: current adapter instance used to interface with broker
        :param port: the serial port device to use.
        :param baudrate: the baudrate that will be set by user.
        :return: returns the instantiated protocol object
        '"""

        # Make sure port is not a list
        port = port[0] if isinstance(port, list) else port
        protocol = PCOMSerial(adapter)
        SerialPort(protocol, port, adapter.reactor, baudrate=baudrate)
        return protocol

    @classmethod
    def get_open_params_defaults(cls):
        """
        Returns a list of parameters defaults. These will be displayed in the UI.
        :return: default args: the default arguments provided to the user in the UI
        """

        default_args = BaseProtocol.get_open_params_defaults()
        potential_serials = [port_list[0] for port_list in list_ports.comports()]
        default_args['port'] = potential_serials
        default_args['baudrate'] = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]

        return default_args

    def close(self):
        """
        Simply close the connection
        :return:
        """

        self.transport.loseConnection()
        return defer.succeed(None)

    def __init__(self, adapter):
        """
        :param adapter: The adapter that will serve as an interface for interacting with the broker
        """
        # A list of items that we will need to discover for.
        # The base protocol will use this dictionary to feed items to
        # the UI
        self.items = []

        # The list of connected item IDs found in the initial sweep in
        # connectionMade()
        self._item_ids = []

        BaseProtocol.__init__(self)

        # Set the LineReceiver to line mode. This causes lineReceived to be called
        # when data is sent to the serial port. We will get a line whenever the END_BYTE
        # appears in the buffer
        self.setLineMode()
        self.delimiter = END_BYTE_STR

        # The buffer that we will be storing the data that arrives via the serial connection
        self._binary_buffer = bytearray()

        self.adapter = adapter

        # Event IDs are 16-bit (2 byte) numbers so we need a radix
        # of 65535 or 0xFFFF in hex
        # NOTE: The number of bits in an event ID is subject to change,
        # the constant NUM_EVENT_ID_BITS can easily be changed to accommodate this.
        self._event_id_generator = message_id_generator((2**self.NUM_EVENT_ID_BITS))

        # From parlay.utils, calls _message_queue_handler() whenever
        # a new message is added to the MessageQueue object
        self._message_queue = MessageQueue(self._message_queue_handler)

        self._attached_item_d = None

        # Dictionary that maps ID # to Deferred object
        self._discovery_msg_ids = {}

        # Sequence number is a nibble as of now, so the domain should be
        # 0 <= seq number <= 15
        # which means the radix will be 16, but to be safe I'll do
        # 2^SEQ_BITS where SEQ_BITS is a member constant that can easily be changed
        self._seq_num = message_id_generator((2**self.SEQ_BITS))

        # ACKs should be deferred objects because you want to catch them on the way
        # back via asynchronous communication.
        self._ack_deferred = defer.Deferred()

        # Store discovered item IDs so that we do not push duplicates to the
        # item requesting the discovery

        self._in_progress = False
        self._discovery_deferred = defer.Deferred()

    def send_error_message(self, original_message, message_status):
        """
        Sends a notification error to the destination ID.

        :param original_message: PCOM Message object that holds the IDs of the sender and receiver
        :param message_status: Message status code that translates to an error message.
        :return:
        """

        error_msg = pcom_message.PCOMMessage(to=original_message.from_, from_=original_message.to,
                                             msg_status=message_status, msg_id=original_message.msg_id)

        json_msg = error_msg.to_json_msg()
        self.adapter.publish(json_msg)

    @defer.inlineCallbacks
    def _message_queue_handler(self, message):
        """
        This is the callback function given to the MessageQueue object that is called
        whenever a new message is added to the queue.

        This function does the actual writing to the serial port.

        :type message dict
        :param message: dictionary message received from Parlay
        """

        s = pcom_message.PCOMMessage.from_json_msg(message)

        # Serialize the message and prepare for protocol wrapping.
        try:
            packet = encode_pcom_message(s)
        except:
            self.send_error_message(original_message=s, message_status=PSTATUS_ENCODING_ERROR)
            defer.returnValue(message)

        need_ack = True

        # Get the next sequence number and then wrap the protocol with
        # the desired low level byte wrapping and send down serial line
        sequence_num = self._seq_num.next()
        packet = str(wrap_packet(packet, sequence_num, need_ack))

        # print "SENT MESSAGE: ", [hex(ord(x)) for x in packet]

        # Write to serial line! Good luck packet.
        self.transport.write(packet)
        num_retries_left = self.NUM_RETRIES

        while need_ack and num_retries_left > 0:
            try:
                ack_sequence_num = yield timeout(self._ack_deferred, .5)
                if ack_sequence_num == sequence_num:
                    need_ack = False
                else:
                    print "Wrong seq num:", ack_sequence_num, "!=", sequence_num

            except TimeoutError:
                print "Timeout occurred. Sending packet again..."
                self._ack_deferred = defer.Deferred()
                self.transport.write(packet)
                num_retries_left -= 1

        defer.returnValue(message)

    def _discovery_listener(self, msg):
        """
        We need did this function to fire the deferred objects based on the msg we receive.
        If the message ID matches an ID in the dictionary, fire the deferred.

        :type msg PCOMMessage

        """
        # Return if there aren't any IDs left
        if len(self._discovery_msg_ids) == 0:
            return

        if msg.category() == MessageCategory.Order_Response and msg.msg_id in self._discovery_msg_ids:
            # If the message was a response and matched an ID in the dictionary, remove it and fire the
            # corresponding Deferred object.
            self._discovery_msg_ids.pop(msg.msg_id).callback(msg)

        return

    """

    The following functions aid in the discovery protocol.
    They may be condensed into fewer functions that require
    more parameters, but I thought abstracting each message
    would making understanding the protocol easier.

    """

    @defer.inlineCallbacks
    def get_property_name(self, to, requested_property_id):
        """
        Sends a message down the serial line requesting the command name of a given command ID,
        used in discovery protocol
        :param to: destination item ID
        :param requested_property_id: property ID that we want to know the name of
        :return: name of the property from Embedded Core
        """

        response = yield self.send_command(to, command_id=GET_PROPERTY_NAME, params=["property id"],
                                           data=[requested_property_id])

        # The data in the response message will be a list,
        # the property name should be in the 0th position
        # and strip the NULL byte.
        defer.returnValue(response.data[0])

    @defer.inlineCallbacks
    def get_command_name(self, to, requested_command_id):
        """
        Sends a messge down the serial line requesting the property name of a given property ID,
        used in discovery protocol
        :param to: destination ID
        :param requested_command_id: command ID that we want to know the name of
        :return: name from Embedded Core
        """

        response = yield self.send_command(to, command_id=GET_COMMAND_NAME, params=["command id"],
                                           data=[requested_command_id])

        # The data in the response message will be a list,
        # the command name should be in the 0th position
        defer.returnValue(response.data[0])

    @defer.inlineCallbacks
    def get_command_input_param_format(self, to, requested_command_id):
        """
        Given a command ID and item ID, sends a message to the item ID requesting
        the format of its input parameters. This functions should return a string
        that describes each parameter. NOTE: variable arrays are indicated with a *.
        Eg. A list of ints would be "*i". See format string details for character->byte
        translation.
        :param to: destination item ID
        :param requested_command_id: command ID that we want the parameter format of
        :return: format string describing input parameters
        """

        response = yield self.send_command(to, command_id=GET_COMMAND_INPUT_PARAM_FORMAT, params=["command id"],
                                           data=[requested_command_id])

        r_val = '' if len(response.data) == 0 else response.data[0]
        defer.returnValue(r_val)

    @defer.inlineCallbacks
    def get_command_input_param_names(self, to, requested_command_id):
        """
        Given an item ID and a command ID, requests the parameter names of the command from the item.
        Returns a list of names (comma delimited) that represent the parameter names.

        TODO: change return value to string?

        Eg. "frequency,duty cycle"
        :param to: destination item ID
        :param requested_command_id: command id to find the parameter names of
        :return: a list of parameter names
        """

        response = yield self.send_command(to, command_id=GET_COMMAND_INPUT_PARAM_NAMES, params=["command id"],
                                           data=[requested_command_id])

        param_names = [] if len(response.data) == 0 else response.data[0].split(',')
        defer.returnValue(param_names)

    @defer.inlineCallbacks
    def get_command_output_parameter_desc(self, to, requested_command_id):
        """
        Given an item ID and a command ID, requests the output description
        Returns a list of names (comma delimited) that represent the output names

        TODO: change return value to string?

        Eg. "frequency,duty cycle"
        :param to: destination item ID
        :param requested_command_id: command id to find the parameter names of
        :return: a list of parameter names
        """

        response = yield self.send_command(to, command_id=GET_COMMAND_OUTPUT_PARAM_DESC, params=["command id"],
                                           data=[requested_command_id])
        list_of_names = [] if len(response.data) == 0 else response.data[0].split(",")
        defer.returnValue(list_of_names)

    @defer.inlineCallbacks
    def get_property_type(self, to, requested_property_id):
        """
        Given a property ID, requests the property's type from the item ID.
        Gets back a format string.

        :param to: destination item ID
        :param requested_property_id: property ID that we want the type of
        :return: format string describing the type
        """

        response = yield self.send_command(to, command_id=GET_PROPERTY_TYPE, params=["property id"],
                                           data=[requested_property_id])

        r_val = '' if len(response.data) == 0 else response.data[0]
        defer.returnValue(r_val)

    def send_command(self, to, tx_type="DIRECT", command_id=0, msg_status="INFO", response_req=True, params=[], data=[]):
        """
                Send a command and return a deferred that will succeed on a response and with the response

        :param to: destination item ID
        :param tx_type: DIRECT or BROADCAST
        :param command_id: ID of the command
        :param msg_status: status of the message: ERROR, WARNING, INFO, PROGRESS, or OK
        :param response_req: boolean whether or not a response is required
        :param params: command parameters
        :param data: data that corresponds to each parameter
        :return:
        """
        # Increment the event ID
        event_id = self._event_id_generator.next()

        # Construct the message based on the parameters

        # For now "FROM:" will always be the discovery code,
        # this needs to change in the future.
        # Build the TOPICS portion
        topics = {
            "MSG_ID": event_id,
            "TX_TYPE": tx_type,
            "MSG_TYPE": "COMMAND",
            "RESPONSE_REQ": response_req,
            "MSG_STATUS": msg_status,
            # NOTE: Change this to handle sending and receiving across subsystems.
            "FROM": self.DISCOVERY_CODE,
            "TO": to
        }

        # Build the CONTENTS portion
        contents = {
            "COMMAND": command_id,
        }

        # If data was given via function arguments we need to pack it
        # into the contents portion of the message to resemble a JSON message.
        for parameter, data_val in zip(params, data):
            contents[parameter] = data_val

        # If we need to wait the result should be a deferred object.
        if response_req:
            result = defer.Deferred()
            # Add the correct mapping to the dictionary
            self._discovery_msg_ids[event_id] = result

        # Message will be added to event queue and
        # sent down serial line (via callback function _message_queue_handler())
        self._message_queue.add({"TOPICS": topics, "CONTENTS": contents})

        # Return the Deferred object if we need to
        return result

    def connectionMade(self):
        """
        The initializer for the protocol. This function is called when a connection to the server
        (broker in our case) has been established. Keep this function LIGHT, it should not take a long time
        to fetch the subsystem and item IDs. The user typically shouldn't notice.

        I wrote a function _get_attached_items() that is called here and also when a discovery takes place.
        :return: None
        """

        self._get_attached_items()
        return

    @defer.inlineCallbacks
    def _get_attached_items(self):
        """
        Populates self.items with all attached item IDs
        NOTE: This is a subroutine of the discovery process. This method should be lightweight because
        it also going to be called upon connection establishment. We don't want the user waiting around forever
        when their device is connected.

        :return:
        """

        # If we have stored systems, return them first
        while self._attached_item_d is not None:
            yield self._attached_item_d

        # Create a new deferred object because this is an asynchronous operation.
        self._attached_item_d = defer.Deferred()

        # The first part of the discovery protocol
        # is to fetch all subsystems. The reactor inside of
        # the embedded core should return with each subsystem as a
        # ID, Name pair (eg. (0, "IO_Control_board"))

        response = yield self.send_command(to=self.BROADCAST_SUBSYSTEM_ID, command_id=0, tx_type="BROADCAST")
        self._subsystem_ids = [int(response.data[0])]
        print "SUBSYSTEMS:", self._subsystem_ids

        # TODO: Explain this in comments
        d = self._attached_item_d
        self._attached_item_d = None
        d.callback(None)

    @staticmethod
    def initialize_command_map(item_id):
        """
        Creates the discovery command entries in the command map for the specified item ID.
        :param item_id: Item ID found during discovery.
        :return: None
        """

        command_map[item_id][GET_ITEM_NAME] = CommandInfo("", [], ["Item name"])
        command_map[item_id][GET_ITEM_TYPE] = CommandInfo("", [], ["Item type"])
        command_map[item_id][GET_COMMAND_IDS] = CommandInfo("", [], ["Command IDs"])
        command_map[item_id][GET_PROPERTY_IDS] = CommandInfo("", [], ["Property IDs"])
        command_map[item_id][GET_COMMAND_NAME] = CommandInfo("H", ["command id"], ["Command name"])
        command_map[item_id][GET_COMMAND_INPUT_PARAM_FORMAT] = CommandInfo("H", ["command id"],
                                                                           ["Command input format"])
        command_map[item_id][GET_COMMAND_INPUT_PARAM_NAMES] = CommandInfo("H", ["command id"], ["Command input names"])
        command_map[item_id][GET_COMMAND_OUTPUT_PARAM_DESC] = CommandInfo("H", ["command id"], ["Command output names"])
        command_map[item_id][GET_PROPERTY_NAME] = CommandInfo("H", ["property id"], ["Property name"])
        command_map[item_id][GET_PROPERTY_TYPE] = CommandInfo("H", ["property id"], ["Property type"])

        return

    @defer.inlineCallbacks
    def get_discovery(self):
        """
        Hitting the "discovery" button on the UI triggers this generator.

        Run a discovery for everything connected to this protocol and return a list of of all connected:
        items, messages, and endpoint types
        """

        print "----------------------------"
        print "Discovery function started!"
        print "----------------------------"

        # If there is a deferred item, yield that first
        if self._attached_item_d is not None:
            yield self._attached_item_d

        # If we were already in the process of a discovery we should
        # return a deferred object.
        if self._in_progress:
            defer.returnValue(self._discovery_deferred)

        self._in_progress = True
        self.items = []
        for subsystem_id in self._subsystem_ids:
            try:
                yield self._get_item_discovery_info(subsystem_id)
            except Exception as e:
                print("Exception while discovering! Skipping subsystem : " + str(subsystem_id) + "\n    " + str(e))

        self._in_progress = False

        # At this point self.items should be populated with
        # the ParlayStandardItem objects that represent the items we discovered.
        # By calling BaseProtocol's get_discovery() function we can get that information
        # to the adapter and furthermore to the broker.
        defer.returnValue(BaseProtocol.get_discovery(self))


    @staticmethod
    def command_cb(command_info_list, item_id, command_id, command_dropdowns, command_subfields, parlay_item):
        """
        Callback function used to update the command map and parlay item dropdown menu when the command info
        is retrieved from the embedded device during discovery. This function is called using gatherResults
        which will only callback once all deferreds have been fired.

        :param command_info_list: Stores the command name, command input format, command input names
        and command output description. This information will be used to populate the ParlayStandardItem.
        :param item_id: 2 byte item ID of the ParlayStandardItem we will be populating
        :param command_id: 2 byte command ID of the command we have the information for
        :param command_dropdowns: dropdown field for the ParlayStandardItem
        :param command_subfields: subfields for each dropdown option of the ParlayStandardItem
        :param parlay_item: ParlayStandardItem that we will be updating
        :return:
        """

        local_subfields = []

        c_name = command_info_list[0]
        c_input_format = command_info_list[1]
        c_input_names = command_info_list[2]
        c_output_desc = command_info_list[3]

        command_map[item_id][command_id] = CommandInfo(c_input_format, c_input_names,
                                                      c_output_desc)
        command_dropdowns.append((c_name, command_id))

        for parameter in c_input_names:
            local_subfields.append(parlay_item.create_field(parameter, INPUT_TYPES.STRING))

        command_subfields.append(local_subfields)


    @staticmethod
    def property_cb(property_info_list, item_id, property_id, parlay_item):
        """

        Callback function that populates the ParlayStandardItem parlay_item with
        the designated property information.

        :param property_info_list: Property name and property type obtained from the embedded device
        :param item_id: 2 byte item ID that we will be populating the ParlayStandardItem of
        :param property_id: 2 byte property ID that represents the property we will updating
        :param parlay_item: ParlayStandardItem object
        :return:
        """

        property_name = property_info_list[0]
        property_type = property_info_list[1]

        property_map[item_id][property_id] = PropertyData(name=property_name, format=property_type)

        parlay_item.add_property(property_id, name=property_name)
        parlay_item.add_datastream(property_id, name=property_name + "_stream")



    @defer.inlineCallbacks
    def _get_item_discovery_info(self, subsystem):
        """
        The discovery protocol for the embedded core:

        GET SUBSYSTEMS IDS
        GET ITEM IDS
        GET ITEM INFORMATION

        Where ITEM INFORMATION is:
            GET ITEM NAME
            GET ITEM TYPE
            GET COMMAND IDS
            GET PROPERTY IDS

            For each command:
                GET COMMAND NAME
                GET COMMAND INPUT PARAM FORMAT
                GET COMMAND INPUT PARAM NAMES
                GET COMMAND OUTPUT PARAM DESCRIPTION

            For each property:
                GET PROPERTY NAME
                GET PROPERTY TYPE

        :param item_id:
        :return:
        """

        # Subsystem ID is the high byte of the item ID
        subsystem_id = subsystem

        # If the item was already discovered attach nothing to
        # the Deferred object's return value.
        # Otherwise add the item ID to the set of already discovered
        # IDs because we are about to discover it!

        # if item_id in self._already_discovered:
        #     defer.returnValue({})
        # else:
        #     # add the item ID to the already_discovered set.
        #     self._already_discovered.add(item_id)

        discovery = {"Subsystem ID": subsystem_id}
        print "Running discovery on subsystem: ", subsystem_id

        # Convert subsystem IDs to ints so that we can send them
        # back down the serial line to retrieve their attached item
        # For each subsystem ID, fetch the items attached to it

        print "Fetching items from subsystem ID: ", subsystem_id
        response = yield self.send_command(subsystem_id << self.SUBSYSTEM_SHIFT, "DIRECT")
        self._item_ids = [int(item_id) for item_id in response.data]  # TODO: Change to extend() to get all item IDs

        print "---> ITEM IDS FOUND: ", self._item_ids

        for item_id in self._item_ids:
            self.adapter.subscribe(self.add_message_to_queue, TO=item_id)
            command_map[item_id] = {}
            property_map[item_id] = {}
            PCOMSerial.initialize_command_map(item_id)

        for item_id in self._item_ids:
            response = yield self.send_command(item_id, command_id=GET_ITEM_NAME, tx_type="DIRECT")
            item_name = str(response.data[0])

            parlay_item = ParlayStandardItem(item_id=item_id, name=item_name)

            response = yield self.send_command(item_id, command_id=GET_ITEM_TYPE, tx_type="DIRECT")

            item_type = str(response.data[0])
            response = yield self.send_command(item_id, command_id=GET_COMMAND_IDS, tx_type="DIRECT")

            command_ids = response.data

            command_dropdowns = []
            command_subfields = []

            parlay_item.add_field('COMMAND', INPUT_TYPES.DROPDOWN,
                                  dropdown_options=command_dropdowns,
                                  dropdown_sub_fields=command_subfields)

            discovered_command = defer.DeferredList([])

            for command_id in command_ids:
                # Loop through the command IDs and build the Parlay Item object
                # for each one

                command_name = self.get_command_name(item_id, command_id)
                command_input_format = self.get_command_input_param_format(item_id, command_id)
                command_input_param_names = self.get_command_input_param_names(item_id, command_id)
                command_output_desc = self.get_command_output_parameter_desc(item_id, command_id)

                discovered_command = defer.gatherResults([command_name, command_input_format, command_input_param_names, command_output_desc])
                discovered_command.addCallback(PCOMSerial.command_cb, item_id=item_id, command_id=command_id,
                                               command_subfields=command_subfields, command_dropdowns=command_dropdowns,
                                               parlay_item=parlay_item)

            yield discovered_command

            response = yield self.send_command(item_id, command_id=GET_PROPERTY_IDS, tx_type="DIRECT")
            property_ids = response.data

            discovered_property = defer.DeferredList([])

            for property_id in property_ids:
                property_name = self.get_property_name(item_id, property_id)
                property_type = self.get_property_type(item_id, property_id)

                discovered_property = defer.gatherResults([property_name, property_type])
                discovered_property.addCallback(PCOMSerial.property_cb, item_id=item_id, property_id=property_id,
                                                parlay_item=parlay_item)

            yield discovered_property

            self.items.append(parlay_item)
        defer.returnValue(discovery)

    def _send_broadcast_message(self):
        """
        Sends broadcast message to the broadcast subsystem ID stored in
        self.BROADCAST_SUBSYSTEM_ID
        :return:
        """

        # The subsystem ID for the broadcast message is 0x80
        # The high byte of the destination ID is the subsystem ID, so we should insert
        # 0x80 into the high byte.
        destination_id = self.BROADCAST_SUBSYSTEM_ID + self.EMBD_REACTOR_ID

        # The response code, event type, event attributes, and format string are all zero for a
        # broadcast message
        return self.send_command(to=destination_id, command_id=0, tx_type="BROADCAST")

    def add_message_to_queue(self, message):
        """
        This will send a packet down the serial line. Subscribe to messages using the adapter

        :param message : A parlay dictionary message
        """

        # add the message to the queue
        self._message_queue.add(message)

    def rawDataReceived(self, data):
        """
        This function is called whenever data appears on the serial port and raw mode is turned on.
        Since this protocol uses line receiving, this function should never be called, so raise an
        excpetion if it is.

        :param data:
        :return:
        """

        raise Exception('Using line received!')

    def _on_packet(self, sequence_num, ack_expected, is_ack, is_nak, msg):
        """
        This will get called with every new serial packet.
        The parameters are the expanded tuple given from unstuff_packet
        :param sequence_num: the sequence number of the received packet
        :param ack_expected: Is an ack expected to this message?
        :param is_ack : Is this an ack?
        :param is_nak: Is this a nak?
        :param msg: The pcom message (if it is one and not an ack/nak)
        :type msg : PCOMMessage
        """

        if is_ack:
            temp = self._ack_deferred
            self._ack_deferred = defer.Deferred()
            temp.callback(sequence_num)
            return
        elif is_nak:
            return  # Ignore, timeout should handle the resend.

        parlay_msg = msg.to_json_msg()
        print "---> Message to be published: ", parlay_msg
        self.adapter.publish(parlay_msg, self.transport.write)

        # If we need to ack, ACK!
        if ack_expected:
            ack = str(p_wrap(ack_nak_message(sequence_num, True)))
            self.transport.write(ack)
            print "---> ACK MESSAGE SENT"
            print [hex(ord(x)) for x in ack]

        # also send it to discovery listener locally
        self._discovery_listener(msg)

    def lineReceived(self, line):
        """
        If this function is called we have received a <line> on the serial port
        that ended in 0x03.

        :param line:
        :return:
        """

        print "--->Line received was called!"
        print [hex(ord(x)) for x in line]

        # Using byte array so unstuff can use numbers instead of strings
        buf = bytearray()
        start_byte_index = (line.find(START_BYTE_STR) + 1)
        buf += line
        packet_tuple = unstuff_packet(buf[start_byte_index:])
        self._on_packet(*packet_tuple)


class CommandInfo:
    """
    CommandInfo is class used to store the information of the commands
    received from the embedded device.
    """

    def __init__(self, fmt, parameters, output_names):
        self.fmt = fmt
        self.params = parameters
        self.output_names = output_names



