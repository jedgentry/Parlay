from parlay.protocols.protocol import BaseProtocol
from parlay.server.broker import Broker, run_in_broker
from twisted.internet import defer
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from parlay.items.parlay_standard import ParlayCommandItem, parlay_command, ParlayProperty, MSG_TYPES, BadStatusError
from parlay.protocols.utils import timeout


class ASCIILineProtocol(BaseProtocol, LineReceiver):
    """
    When a client connects over a serial, this is the protocol that will handle the communication.
    The messages are encoded as a JSON string
    """

    broker = Broker.get_instance()

    def __init__(self, port):
        self._new_data = defer.Deferred()
        self._parlay_name = port
        if not hasattr(self, "items"):
            self.items = [LineItem(self._parlay_name, self._parlay_name, self)]
        BaseProtocol.__init__(self)

    @classmethod
    def open(cls, broker, port="/dev/tty.usbserial-FTAJOUB2", baudrate=57600, delimiter="\n"):
        """
        This will be called bvy the system to construct and open a new SSCOM_Serial protocol
        :param cls : The class object (supplied by system)
        :param broker:  current broker insatnce (supplied by system)
        :param port: the serial port device to use. On linux, something like "/dev/ttyUSB0". On windows something like "COM0"
        :param baudrate: baudrate of serial connection
        :param delimiter:
        """
        if isinstance(port, list):
            port = port[0]

        p = cls(port)
        cls.delimiter = str(delimiter).decode("string_escape")

        SerialPort(p, port, broker._reactor, baudrate=baudrate)

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
        pass

    def __str__(self):
        return "Serial Terminal @ " + self._parlay_name

    @run_in_broker
    def wait_for_data(self, timeout_secs=None):
        """
        Call this to wait until there is data from the serial line.
        If threaded: Will block. Return value is serial line data
        If Async   : Will not blocl. Return value is Deferred that will be called back with serial line data
        :param timeout_secs : Timeout if you don't get data in time. None if no timeout
        :type timeout_secs : int|None
        """
        assert timeout_secs is None or timeout_secs >= 0
        return timeout(self._new_data, timeout_secs)

    @run_in_broker
    def got_new_data(self, data):
        """
        Call this when you have new data and want to pass it to any waiting Items
        """
        old_new_data = self._new_data

        # setup the new data in case it causes a callback to fire
        self._new_data = defer.Deferred()
        old_new_data.callback(data)


class LineItem(ParlayCommandItem):

    LAST_LINE_RECEIVED = ParlayProperty(val_type=str, default="")

    def __init__(self, item_id, name, protocol):
        ParlayCommandItem.__init__(self, item_id, name)
        self._protocol = protocol

    @parlay_command(async=True)
    def send_raw_data(self, data):
        self._protocol.sendLine(str(data))

    def wait_for_data(self, timeout_secs=3):
        return self._protocol.wait_for_data(timeout_secs)
