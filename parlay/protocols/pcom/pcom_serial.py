"""

PCOM_Serial.py

This protocol enables Parlay to interact with embedded devices. This class handles the passing of messages
between Parlay and embedded devices.


"""


from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from twisted.internet import defer

# Testing
from parlay import parlay_command, start
# Testing
from parlay.protocols.serial_line import ASCIILineProtocol, LineItem

from parlay.items.parlay_standard import ParlayStandardItem, INPUT_TYPES
from parlay.protocols.base_protocol import BaseProtocol
from parlay.protocols.utils import message_id_generator, timeout, MessageQueue, TimeoutError, delay
from serial.tools import list_ports
import pcom_message
from serial_encoding import *
from collections import namedtuple
import struct
import time

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

PropertyData = namedtuple('PropertyData', 'name format')
class PCOM_Serial(BaseProtocol, LineReceiver):

    # Command code is 0x00 for discovery

    NUM_RETRIES = 3
    DISCOVERY_SERVICE_CODE = 0xfefe


    # The minimum event ID. Some event IDs may need to be reserved
    # in the future.
    MIN_EVENT_ID = 0
    NUM_EVENT_ID_BITS = 16

    # Number of bits we have for sequence number
    SEQ_BITS = 4


    @classmethod
    def open(cls, broker, port, baudrate):
        '''

        :param cls: The class object (supplied by system)
        :param broker: current broker instance (supplied by system)
        :param port: the serial port device to use. On linux, something like/dev/ttyUSB0
        :return: returns the instantiated protocol object

        '''

        # Make sure port is not a list
        port = port[0] if isinstance(port, list) else port

        protocol = PCOM_Serial(broker)
        print "Serial Port constructed with port " + str(port)
        SerialPort(protocol, port, broker.reactor, baudrate=57600)

        return protocol

    @classmethod
    def get_open_params_defaults(cls):

        '''
        Returns a list of parameters defaults. These will be displayed in the UI.
        :return:
        '''

        default_args = BaseProtocol.get_open_params_defaults()

        potential_serials =  [port_list[0] for port_list in list_ports.comports()]
        default_args['port'] = potential_serials
        default_args['baudrate'] = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]

        return default_args

    def close(self):
        '''
        Simply close the connectection
        :return:
        '''
        self.transport.loseConnection()
        return defer.succeed(None)

    def __init__(self, broker):
        """
        :param broker: The Broker singleton that will route messages
        :param system_ids: A list of system_ids that are connected, or None to do a discovery

        """

        # A list of items that we will need to discover for.
        # The base protocol will use this dictionary to feed items to
        # the UI
        self.items = []
        self.item_ids = []

        # Store a map of Item IDs -> Command ID -> Command Objects
        # Command objects will store the parameter -> format mapping
        self._command_map = {}

        # Store a map of properties. We must keep track of a
        # name -> format mapping in order to serialize data
        self._property_map = {}

        BaseProtocol.__init__(self)

        # Set the LineReceiver to line mode. This causes lineReceived to be called
        # when data is sent to the serial port. We will get a line whenever the END_BYTE
        # appears in the buffer
        self.setLineMode()
        self.delimiter = END_BYTE_STR

        # The buffer that we will be storing the data that arrives via the serial connection
        self._binary_buffer = bytearray()

        self.broker = broker

        # Event IDs are 16-bit (2 byte) numbers so we need a radix
        # of 65535 or 0xFFFF in hex
        # NOTE: The number of bits in an event ID is subject to change,
        # the constant NUM_EVENT_ID_BITS can easily be changed to accommodate this.
        self._event_id_generator = message_id_generator((2**self.NUM_EVENT_ID_BITS))

        # From parlay.utils, calls _send_message_down_transport() whenever
        # a new message is added to the MessageQueue object
        self._message_queue = MessageQueue(self._send_message_down_transport)

        self._attached_system_d = None

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

    def _get_data_format(self, msg):
        '''
        Takes a msg and does the appropriate table lookup to obtain the
        format data for the command/property/stream.

        Returns a tuple in the form of (data, format)
        where data is a list and format is a format string.

        :param msg:
        :return:
        '''

        data = []
        format = ''

        if msg.msg_type == "COMMAND":
            # If the message type is "COMMAND" there should be an
            # entry in the 'CONTENTS' table for the command ID
            if msg.to in self._command_map:
                # TODO: Check if s.contents['COMMAND'] is in the second level of the map
                # command will be a CommandInfo object that has a list of parameters and format string
                command = self._command_map[msg.to][msg.contents['COMMAND']]
                format = command.fmt
                for param in command.params:
                    data.append(msg.contents[param] if msg.contents[param] is not None else 0)

        elif msg.msg_type == "PROPERTY":
            # If the message type is a "PROPERTY" there should be
            # a "PROPERTY" entry in the "CONTENTS" that has the property ID

            if msg.to in self._property_map:
                property = self._property_map[msg.to][msg.contents['PROPERTY']]
                format = property.format
                data.append(msg.contents['VALUE'] if msg.contents['VALUE'] is not None else 0)

        return (data, format)




    @defer.inlineCallbacks
    def _send_message_down_transport(self, message):
        """
        This is the callback function given to the MessageQueue object that is called
        whenever a new message is added to the queue.

        This function does the actual writing to the serial port.

        :type message dict
        """


        # Turn it into a pcom message that we can understand.
        s = pcom_message.PCOMMessage.from_dict_msg(message)
        s.data, s.format_string = self._get_data_format(s)
        print "DATA:", s.data
        print "FORMAT: ", s.format_string

        # Serialize the message and prepare for protocol wrapping.
        packet = encode_pcom_message(s)
        need_ack = True

        # Get the next sequence number and then wrap the protocol with
        # the desired low level byte wrapping and send down serial line
        sequence_num = self._seq_num.next()
        packet = str(wrap_packet(packet, sequence_num, need_ack))

        print "SENT MESSAGE: ", [hex(ord(x)) for x in packet]
        # Write to serial line! Good luck packet.
        self.transport.write(packet)

        num_retries_left = self.NUM_RETRIES
        while need_ack and num_retries_left > 0:
            try:
                ack_sequence_num = yield timeout(self._ack_deferred, .5)
                if ack_sequence_num == sequence_num:
                    need_ack = False  # we got it, no need to wait
                else:
                    print "Wrong Seq Num? ", ack_sequence_num, "!=", sequence_num
            except TimeoutError:
                # retry
                print "RETRY"
                self._ack_deferred = defer.Deferred()  # set up a new one
                self.transport.write(packet)  # try again
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

        if msg.category() == MessageType.Order_Response and msg.msg_id in self._discovery_msg_ids:
            # If the message was a response and matched an ID in the dictionary, remove it and fire the
            # corresponding Deferred object.
            self._discovery_msg_ids.pop(msg.msg_id).callback(msg)


    '''

    The following functions aid in the discovery protocol.
    They may be condensed into fewer functions that require
    more parameters, but I thought abstracting each message
    would making understanding the protocol easier.

    '''

    @defer.inlineCallbacks
    def get_property_name(self, to, requested_property_id):
        '''
        Sends a message down the serial line requesting the command name of a given command ID,
        used in discovery protocol
        :param to: destination item ID
        :param requested_property_id: property ID that we want to know the name of
        :return: name of the property from Embedded Core
        '''

        response = yield self.send_command(to, command_id=GET_PROPERTY_NAME, params=["property id"], data=[requested_property_id])

        # The data in the response message will be a list,
        # the property name should be in the 0th position
        # and strip the NULL byte.
        defer.returnValue(response.data[0])

    @defer.inlineCallbacks
    def get_command_name(self, to, requested_command_id):
        '''
        Sends a message down the serial line requesting the property name of a given property ID,
        used in discovery protocol
        :param to: destination ID
        :param requested_command_id: command ID that we want to know the name of
        :return: name from Embedded Core
        '''

        response = yield self.send_command(to, command_id=GET_COMMAND_NAME, params=["command id"], data=[requested_command_id])

        # The data in the response message will be a list,
        # the command name should be in the 0th position
        defer.returnValue(response.data[0])

    @defer.inlineCallbacks
    def get_command_input_param_format(self, to, requested_command_id):
        '''
        Given a command ID and item ID, sends a message to the item ID requesting
        the format of its input parameters. This functions should return a string
        that describes each parameter. NOTE: variable arrays are indicated with a *.
        Eg. A list of ints would be "*i". See format string details for character->byte
        translation.
        :param to: destination item ID
        :param requested_command_id: command ID that we want the parameter format of
        :return: format string describing input parameters
        '''

        response = yield self.send_command(to, command_id=GET_COMMAND_INPUT_PARAM_FORMAT, params=["command id"], data=[requested_command_id])

        print "---> INPURT PARAM FORMAT"

        r_Val = '' if len(response.data) == 0 else response.data[0]
        defer.returnValue(r_Val)

    @defer.inlineCallbacks
    def get_command_input_param_names(self, to, requested_command_id):
        '''
        Given an item ID and a command ID, requests the parameter names of the command from the item.
        Returns a list of names (comma delimited) that represent the parameter names.

        TODO: change return value to string?

        Eg. "frequency,duty cycle"
        :param to: destination item ID
        :param requested_command_id: command id to find the parameter names of
        :return: a list of parameter names
        '''

        print "Fetching input parameter names of command ID: ", requested_command_id
        response = yield self.send_command(to, command_id=GET_COMMAND_INPUT_PARAM_NAMES, params=["command id"], data=[requested_command_id])
        print "RAW INPUT NAMES: ", response.data

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

        response = yield self.send_command(to, command_id=GET_COMMAND_OUTPUT_PARAM_DESC, params=["command id"], data=[requested_command_id])
        list_of_names = [] if len(response.data) == 0 else response.data[0].split(",")

        "---> PARAMETER DESCRIPTION ", response.data
        defer.returnValue(list_of_names)


    @defer.inlineCallbacks
    def get_property_type(self, to, requested_property_id):
        '''
        Given a property ID, requests the property's type from the item ID.
        Gets back a format string.

        :param to: destination item ID
        :param requested_property_id: property ID that we want the type of
        :return: format string describing the type
        '''
        response = yield self.send_command(to, command_id=GET_PROPERTY_TYPE, params=["property id"], data=[requested_property_id])
        print "PROPERTY TYPE: ", response.data
        r_Val = '' if len(response.data) == 0 else response.data[0]
        defer.returnValue(r_Val)


    def send_command(self, to, tx_type="DIRECT", command_id=0, msg_status="INFO", response_req=True, params=[], data=[]):
        """

        Send a command and return a deferred that will succeed on a response and with the response

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
                "FROM": self.DISCOVERY_SERVICE_CODE,
                "TO": to

        }

        # Build the CONTENTS portion
        contents = {
                "COMMAND": command_id,
        }

        # If data was given via function arguments we need to pack it
        # into the contents portion of the message to resemble a JSON message.
        for data_pair in zip(params,data):
            contents[data_pair[0]] = data_pair[1]

        # If we need to wait the result should be a deferred object.
        if response_req:
            result = defer.Deferred()
            # Add the correct mapping to the dictionary
            self._discovery_msg_ids[event_id] = result

        # Message will be added to event queue and
        # sent down serial line (via callback function _send_down_transport())
        self._message_queue.add({"TOPICS": topics, "CONTENTS": contents})

        # Return the Deferred object if we need to
        return result

    def connectionMade(self):
        '''
        The initializer for the protocol. This function is called when a connection to the server
        (broker in our case) has been established. Keep this function LIGHT, it should not take a long time
        to fetch the subsystem and item IDs. The user typically shouldn't notice.

        I wrote a function _get_attached_systems() that is called here and also when a discovery takes place.
        :return: None
        '''
        self._get_attached_systems()
        return

    @defer.inlineCallbacks
    def _get_attached_systems(self):
        '''
        A generator that returns all attached system IDs
        NOTE: This is a subroutine of the discovery process. This method should be lightweight because
        it also going to be called upon connection establishment. We don't want the user waiting around forever
        when their device is connected.

        :return: All attached system IDs

        '''

        # If we have stored systems, return them first
        while self._attached_system_d is not None:
            yield self._attached_system_d

        # Create a new deferred object because this is an asynchronous operation.
        self._attached_system_d = defer.Deferred()

        # The first part of the discovery protocol
        # is to fetch all subsystems. The reactor inside of
        # the embedded core should return with each subsystem as a
        # ID, Name pair (eg. (0, "IO_Control_board"))

        subsystems = yield self._get_subsystems()
        print "SUBSYTESMS", subsystems

        # Convert subsystem IDs to ints so that we can send them
        # back down the serial line to retrieve their attached item
        # For each subsystem ID, fetch the items attached to it

        for subsystem in subsystems:
            print "Fetching items from subsystem ID: ", subsystem
            response = yield self.send_command((1 << 8), "DIRECT")
            self.item_ids = [int(item_id) for item_id in response.data]

        print "---> ITEM IDS FOUND: ", self.item_ids

        print "---> Subscribing to broker"
        for item_id in self.item_ids:
            self.broker.subscribe(self.add_message_to_queue, TO=item_id)
            self._command_map[item_id] = {}
            self._property_map[item_id] = {}
            self._command_map[item_id][GET_ITEM_NAME] = CommandInfo("",[])
            self._command_map[item_id][GET_ITEM_TYPE] = CommandInfo("", [])
            self._command_map[item_id][GET_COMMAND_IDS] = CommandInfo("",[])
            self._command_map[item_id][GET_PROPERTY_IDS] = CommandInfo("",[])
            self._command_map[item_id][GET_COMMAND_NAME] = CommandInfo("H", ["command id"])
            self._command_map[item_id][GET_COMMAND_INPUT_PARAM_FORMAT] = CommandInfo("H", ["command id"])
            self._command_map[item_id][GET_COMMAND_INPUT_PARAM_NAMES] = CommandInfo("H", ["command id"])
            self._command_map[item_id][GET_COMMAND_OUTPUT_PARAM_DESC] = CommandInfo("H", ["command id"])
            self._command_map[item_id][GET_PROPERTY_NAME] = CommandInfo("H", ["property id"])
            self._command_map[item_id][GET_PROPERTY_TYPE] = CommandInfo("H", ["property id"])


        # TODO: Explain this in comments
        d = self._attached_system_d
        self._attached_system_d = None
        d.callback(None)

    @defer.inlineCallbacks
    def _get_subsystems(self):
        '''
        Sends a broadcast message. A broadcast message goes to the reactor and expects a list of
        subsystems in return.
        :return:
        '''

        # NOTE: Multiple messages may be sent back for the subsystem
        sub_systems = []
        response = yield self._send_broadcast_message()
        sub_systems.extend(response.data)
        defer.returnValue(sub_systems)

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

        # If there is a deferred system, yield that first
        if self._attached_system_d is not None:
            yield self._attached_system_d

        # Initialize a discovered set. We don't want duplicates.
        already_discovered = set()
        for item_id in self.item_ids:
            print "ITEM ID: ", item_id, " in ", self.item_ids
            try:
                yield self._fetch_system_discovery(item_id, already_discovered)
            except Exception as e:
                print("Exception while discovering! Skipping system : " + str(item_id) + "\n    " + str(e))

        defer.returnValue(BaseProtocol.get_discovery(self))

    @defer.inlineCallbacks
    def _fetch_system_discovery(self, item_id, already_discovered):

        # Subsystem ID is the high byte of the item ID
        # Note sure if I'll need this yet.
        subsystem_id = item_id << 8


        # If the item was already discovered attach nothing to
        # the Deferred object's return value.
        # Otherwise add the item ID to the set of already discovered
        # IDs because we are about to discover it!
        if item_id in already_discovered:
            defer.returnValue({})
        else:
            # add the item ID to the already_discovered set.
            already_discovered.add(item_id)

        discovery = {"Subsystem ID": subsystem_id}
        print "Running discovery on subsystem: ", subsystem_id

        response = yield self.send_command(item_id, command_id=GET_ITEM_NAME, tx_type="DIRECT")
        item_name = str(response.data[0][:-1])

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

        for command_id in command_ids:
            # Loop through the command IDs and build the Parlay Item object
            # for each one

            local_subfields = []
            command_name = yield self.get_command_name(item_id, command_id)
            command_input_format = yield self.get_command_input_param_format(item_id, command_id)
            command_input_param_names = yield self.get_command_input_param_names(item_id, command_id)
            command_output_desc = yield self.get_command_output_parameter_desc(item_id, command_id)
            self._command_map[item_id][command_id] = CommandInfo(command_input_format, command_input_param_names)

            command_dropdowns.append((command_name[:-1], command_id))

            for parameter in command_input_param_names:
                local_subfields.append(parlay_item.create_field(parameter, INPUT_TYPES.STRING))

            command_subfields.append(local_subfields)

        response = yield self.send_command(item_id, command_id=GET_PROPERTY_IDS, tx_type="DIRECT")

        property_ids = response.data

        for property_id in property_ids:
            property_name = yield self.get_property_name(item_id, property_id)
            property_type = yield self.get_property_type(item_id, property_id)
            self._property_map[item_id][property_id] = PropertyData(name=property_name, format=property_type)

            print "--> Property name: ", property_name

            parlay_item.add_property(property_id, name=property_name)

        self.items.append(parlay_item)

        defer.returnValue(discovery)



    def _send_broadcast_message(self):

        # The item ID of the reactor is 0, which is where we want our broadcast message to go to.
        device_id = 0

        destination_id = device_id

        # The subsystem ID for the broadcast message is 0x80
        # The high byte of the destination ID is the subsystem ID, so we should insert
        # 0x80 into the high byte.
        destination_id += 0x8000

        # The response code, event type, event attributes, and format string are all zero for a
        # broadcast message
        return self.send_command(to=destination_id, command_id=0, tx_type="BROADCAST")

    def add_message_to_queue(self, message):
        """
        This will send a packet down the serial line. Subscribe to messages using the broker

        :param message : A parlay dictionary message
        """
        # add the message to the queue
        self._message_queue.add(message)


    def _encode_event(self, event_id, from_id, to_id, response_code, event_type, event_attrs, format_string, data=None):
        '''
        :param event_id: Identifier that is unique to the event.
        :param from_id: AKA source ID. This will be the ID of the device in which the event comes from.
        :param to_id: AKA destination ID. This will be the ID of the device that receives this message.
        :param response_code: Depending on the type of event, this could be a command ID, property ID, or status code.
        :param event_type: The type of message. Bits 0-3 are the subtype and bits 4-7 are the category.
        :param event_attrs: Attributes of the event.
                            Bit 0 is the priority of the event. A 0 represents normal priority
                            and a 1 represents a high priority. High priority events are placed in the front of the queue
                            (eg. an interrupt).
                            Bit 1 is the response expected. It applies to orders only and is a way to send a command
                            or property set without getting a response. (0 = response expected, 1 = no response expected).

        :param format_string: Describes the structure of the data using a character for each type.
                                -------------------------------------------------
                                | Type              | Character     | # bytes   |
                                |-------------------|---------------|-----------|
                                | unsigned byte     |    B          |    1      |
                                |-------------------|---------------|-----------|
                                | signed byte       |    b          |    1      |
                                |-------------------|---------------|-----------|
                                | padding           |    x          |    1      |
                                |-------------------|---------------|-----------|
                                | character         |    c          |    1      |
                                |-------------------|---------------|-----------|
                                | unsigned short    |    H          |    2      |
                                |-------------------|---------------|-----------|
                                | signed short      |    h          |    2      |
                                |-------------------|---------------|-----------|
                                | unsigned int      |    I          |    4      |
                                |-------------------|---------------|-----------|
                                | signed int        |    i          |    4      |
                                |-------------------|---------------|-----------|
                                | unsigned long     |    Q          |    8      |
                                |-------------------|---------------|-----------|
                                | signed long       |    q          |    8      |
                                |-------------------|---------------|-----------|
                                | float             |    f          |    4      |
                                |-------------------|---------------|-----------|
                                | double            |    d          |    8      |
                                |-------------------|---------------|-----------|
                                | string            |    s          |    ?      |
                                |-------------------|---------------|-----------|

        :param data:
        :return: Returns a string of bytes
        '''


        # Build the sequence of bytes that is to be sent serially to the Embedded Core Reactor

        buffer = ''
        buffer += struct.pack("<H", event_id)
        buffer += struct.pack("<H", from_id)
        buffer += struct.pack("<H", to_id)
        buffer += struct.pack("<H", response_code)
        buffer += struct.pack("<B", event_type)
        buffer += struct.pack("<B", event_attrs)
        buffer += struct.pack("<s", format_string)

        # Don't send data if there isn't any to send.
        if data is not None:
            buffer += struct.pack("<s", data)

        return buffer

    def _p_wrap(self, stream):
        '''
        Do the promenade wrap! The promenade protocol looks like:

        START BYTE <byte sequence> END BYTE

        Where START BYTE and END BYTE are 0x02 and 0x02 (for now at least).

        Since there is a possibility of 0x02 and 0x03 appearing in the data stream we must added 0x10 to all
        0x10, 0x02, 0x03 bytes and 0x10 should be inserted before each "problem" byte.

        For example

        stream = 0x03 0x04 0x05 0x06 0x07
        _p_wrap(stream) = 0x02 0x10 0x13 0x04 0x05 0x06 0x07 0x03

        :param stream: A raw stream of bytes
        :return: A bytearray that has been run through the Promenade protocol


        '''

        msg = bytearray()
        msg.append(START_BYTE) # START
        for b in stream:
            if b in [START_BYTE, ESCAPE_BYTE, END_BYTE]:
                msg.append(ESCAPE_BYTE)
                msg.append(b + ESCAPE_BYTE)
            else:
                msg.append(b)
        msg.append(END_BYTE)
        return msg

    def rawDataReceived(self, data):
        '''
        This function is called whenever data appears on the serial port
        :param data:
        :return:
        '''

        raise Exception('Using line received!')

    def _on_packet(self, sequence_num, ack_expected, is_ack, is_nak, msg):
        """
        This will get called with every new serial packet.
        The parameters are the expanded tuple gicen from unstuff_packet
        :param sequence_num: the sequence number of the received packet
        :param ack_expected: Is an ack expected to this message?
        :param is_ack : Is this an ack?
        :param is_nak: Is this a nak?
        :param msg: The pcom message (if it is one and not an ack/nak)
        :type msg : PCOMMessage
        """

        if is_ack:
            # let everyone know we got the ack and make a new deferred
            temp = self._ack_deferred   # temp handle
            self._ack_deferred = defer.Deferred()  # setup a new one for everyone to listen to
            temp.callback(sequence_num)  # callback and invalidate the old deferred
            return
        elif is_nak:
            return  # ignore, the timeout will happen and handle a resend

        parlay_msg = msg.to_dict_msg()
        print "---> Message to be published: ", parlay_msg
        self.broker.publish(parlay_msg, self.transport.write)

        # If we need to ack, ACK!
        if ack_expected:
            ack = str(self._p_wrap(ack_nak_message(sequence_num, True)))
            self.transport.write(ack)
            print "---> ACK MESSAGE SENT"
            print [hex(ord(x)) for x in ack]

        # also send it to discovery listener locally
        #print 'About to call listener'
        self._discovery_listener(msg)

    def lineReceived(self, line):
        '''
        If this function is called we have received a <line> on the serial port
        that ended in 0x03.


        :param line:
        :return:
        '''

        print "--->Line received was called!"
        print [hex(ord(x)) for x in line]

        #Using byte array so unstuff can use numbers instead of strings
        buf = bytearray()
        start_byte_index = (line.find(START_BYTE_STR) + 1)
        buf += line
        packet_tuple = unstuff_packet(buf[start_byte_index:])
        self._on_packet(*packet_tuple)


class CommandInfo:

    def __init__(self, fmt, parameters):

        self.fmt = fmt
        self.params = parameters

class SerialLEDItem(LineItem):

	def __init__(self, led_index, item_id, name, protocol):
		LineItem.__init__(self, item_id, name, protocol)
		self._led_index = led_index

if __name__ == "__main__":
	start()


