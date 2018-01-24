from parlay.protocols.base_protocol import BaseProtocol
from parlay.server.broker import Broker
from twisted.internet import defer
from twisted.internet.serialport import SerialPort, serial
from serial.serialutil import SerialException
from twisted.protocols.basic import LineReceiver
from parlay.items.parlay_standard import ParlayCommandItem, parlay_command, ParlayProperty, BadStatusError
from serial.tools import list_ports
import re


class ASCIILineProtocol(BaseProtocol, LineReceiver):
    """
    When a client connects over a serial, this is the protocol that will handle the communication.
    The messages are encoded as a JSON string
    """

    broker = Broker.get_instance()
    open_ports = set()

    def __init__(self, port):
        self._parlay_name = port
        if not hasattr(self, "items"):
            self.items = [LineItem(self._parlay_name, self._parlay_name, self)]
        BaseProtocol.__init__(self)

    @classmethod
    def open(cls, broker, port="/dev/tty.usbserial-FTAJOUB2", baudrate=57600, delimiter="\n",
             bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE):
        """
        This will be called bvy the system to construct and open a new SSCOM_Serial protocol
        :param cls : The class object (supplied by system)
        :param broker:  current broker instance (supplied by system)
        :param port: the serial port device to use. On linux, something like "/dev/ttyUSB0". On windows something like 
        "COM0"
        :param baudrate: baudrate of serial connection
        :param delimiter: The delimiter to token new lines off of.
        :param bytesize: The number of data bits.
        :param parity: The number of parity bits.
        :param stopbits: The number of stop bits.
        """
        if isinstance(port, list):
            port = port[0]

        p = cls(port)
        cls.delimiter = str(delimiter).decode("string_escape")
        try:
            SerialPort(p, port, broker.reactor, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
        except (SerialException, OSError):
            raise BadStatusError("Unable to open serial port. Check that you have administrator privileges.")
        return p

    @classmethod
    def get_open_params_defaults(cls):
        """Override base class function to show dropdowns for defaults"""
        from serial.tools import list_ports

        defaults = BaseProtocol.get_open_params_defaults()

        potential_serials = [x[0] for x in list_ports.comports()]
        defaults['port'] = potential_serials
        defaults['baudrate'] = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]
        defaults['delimiter'] = "\n"
        defaults['bytesize'] = 8
        defaults['parity'] = "N"
        defaults['stopbits'] = 1

        return defaults

    def close(self):
        self.transport.loseConnection()
        return defer.succeed(None)  # fake deferred since we don't have anything asynchronous to do

    def lineReceived(self, line):
        for item in self.items:
            item.LAST_LINE_RECEIVED = line

        # send to all children who are waiting for it
        self.got_new_data(line)

    def rawDataReceived(self, data):
        self.got_new_data(data)

    def __str__(self):
        return "Serial Terminal @ " + self._parlay_name


class LineItem(ParlayCommandItem):
    LAST_LINE_RECEIVED = ParlayProperty(val_type=str, default="")

    def __init__(self, item_id, name, protocol):
        ParlayCommandItem.__init__(self, item_id, name)
        self._protocol = protocol

    @parlay_command(async=True)
    def send_raw_data(self, data):
        return self._protocol.sendLine(str(data))

    @parlay_command(async=True)
    def wait_for_data(self, timeout_secs=300):
        """
        :type timeout_secs float
        """
        return self._protocol.get_new_data_wait_handler().wait(timeout_secs)

    @parlay_command(async=True)
    def send_and_wait(self, data, timeout_secs=300):
        """
        Send and then wait for a single response
        """
        self.send_raw_data(data)
        return self.wait_for_data(timeout_secs)


class USBASCIILineProtocol(ASCIILineProtocol):
    """
    This protocol should be used instead of ASCIILineProtocol when using a USB->Serial adapter to communicate serially
    with devices. Additional filtering options can be provided in the open() function in order to automatically connect
    and open the device.
    """

    NUM_REQUIRED_MATCHING_PORTS = 1
    DEFAULT_BAUD = 115200

    class USBASCIIException(Exception):
        """
        Class used for generating exceptions from the USBASCIILineProtocol class.
        """
        ERROR_STRING_HEADER = "[USBASCIILineProtocol]"

        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return "{0}: {1}\n".format(USBASCIILineProtocol.USBASCIIException.ERROR_STRING_HEADER, self.msg)

    def __init__(self, port):
        """
        Simply calls the ASCIILineProtocol's initializer function
        :param port: Name associated with this protocol in the Parlay ecosystem.
        """
        ASCIILineProtocol.__init__(self, port)

    @classmethod
    def open(cls, adapter, port_vendor_id=None, port_product_id=None, port_descriptor_regex_string=None, delimiter="\n",
             baudrate=DEFAULT_BAUD, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
             stopbits=serial.STOPBITS_ONE):
        """
        Called by the Parlay ecosystem to construct a new USBASCIILineProtocol instance. For example, this function
        is called when the UI button "connect" is pressed.
        :param adapter: Current adapter instance.
        :param port_descriptor_regex_string: Regex string that will be matched with the USB descriptor. For example,

                            port_name_regex_string = "ST( |-)LINK"

                            can be used for matching "ST LINK" or "ST-LINK"

        :param port_vendor_id: Vendor ID of the USB port we wish to automatically connect to. NOTE: Both vendor ID
        and product ID must match the port.
        :param port_product_id: Product ID of the USB port we wish to automatically connect to. NOTE: Both vendor ID
        and product ID must match the port.
        :param delimiter: The delimiter to token new lines off of.
        :param baudrate: The baud rate of the serial connection.
        :param bytesize: Size of each byte for the serial connection.
        :param parity: Bit parity of the serial connection.
        :param stopbits: Number of stop bits for the serial connection.
        :return: Instantiated protocol
        """

        # Make sure user passed in Vendor and Product ID. Note: these parameters have default options so that
        # the type signature matches that of the base class.
        if not port_vendor_id or not port_product_id:
            raise USBASCIILineProtocol.USBASCIIException("Invalid arguments. Both vendor ID and product ID are required"
                                                         "for filtering.")

        # Compile regex if necessary
        port_descriptor_regex = re.compile(port_descriptor_regex_string) if port_descriptor_regex_string else None

        # Get the filtered port list
        matching_ports = USBASCIILineProtocol._filter_ports(list_ports.comports(), port_vendor_id, port_product_id,
                                                            port_descriptor_regex)

        # If we found something other than 1 match, raise an exception.
        if len(matching_ports) != cls.NUM_REQUIRED_MATCHING_PORTS:
            raise USBASCIILineProtocol.USBASCIIException("Number of ports matching filter requirements was not equal to"
                                                         " {0}. Make sure the filter parameters match exactly {0} port(s)"
                                                         ". Use the usb_identifier.py tool in parlay/utils for"
                                                         " information on the currently connected USB ports."
                                                         .format(str(cls.NUM_REQUIRED_MATCHING_PORTS)
            ))

        # Open the ASCIILineProtocol on the found port
        return super(USBASCIILineProtocol, cls).open(adapter, matching_ports[0], baudrate=baudrate, delimiter=delimiter,
                                      bytesize=int(bytesize), parity=parity, stopbits=int(stopbits))

    @classmethod
    def get_open_params_defaults(cls):
        """
        Used for determining default options for open() function call through Parlay ecosystem
        :return: Dictionary of the default options
        """
        # Assign BaseProtocol defaults to our default dictionary to start
        defaults = BaseProtocol.get_open_params_defaults()
        # Assign typical baud rates values
        defaults['baudrate'] = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]
        # Assign typical delimiters
        defaults['delimiter'] = ["\n", "\r"]
        # Assign typical byte sizes for serial coms
        defaults['bytesize'] = [8]
        # Assign typical parity for serial coms
        defaults['parity'] = ["N"]
        # Assign typical number of stop bits for serial coms
        defaults['stopbits'] = [1]
        # Return dictionary
        return defaults

    @staticmethod
    def _match_usb_port(list_port_obj, vendor_id, product_id, name_compiled_regex):
        """
        Given a regular expression for the descriptor, a vendor ID, and a product ID, returns True if the ListPortInfo
        object matches.

        The vendor ID and product ID MUST match the USB device. The descriptor  (name) only needs to match if one is
        provided.

        :param name_regex: Regular expression that will be matched against the USB descriptor if provided
        :param vendor_id:  Number that will be matched against the vendor ID
        :param product_id: Number that will be matched against the product ID
        :return: Boolean, true if matches the provided ListPortInfo
        """
        # Start <is_match> variable true
        is_match = 1
        # Use bitwise operation to AND in the matching of the regex (defaults to True if no regex provided)
        is_match &= bool(not name_compiled_regex or name_compiled_regex.search(list_port_obj.description))
        # AND in vendor ID match
        is_match &= list_port_obj.vid == int(vendor_id)
        # AND in product ID match
        is_match &= list_port_obj.pid == int(product_id)
        # Return boolean determining if match occurred.
        return is_match

    @staticmethod
    def _filter_ports(port_list, vendor_id, product_id, name_compiled_regex):
        """
        Filters the connected COM ports and returns a list of those that match the specified criteria (vendor ID,
        product ID, descriptor regex match).

        :param vendor_id: Vendor ID number to match
        :param product_id: Product ID number to match
        :param name_compiled_regex: Regex description to match
        :return: List of ports that match
        """
        # Filter port list to those that match
        filtered = filter(lambda port: USBASCIILineProtocol._match_usb_port(port, vendor_id, product_id, name_compiled_regex),
                          port_list)
        # Map each matching port to its string path
        return map(lambda port: port.device, filtered)





