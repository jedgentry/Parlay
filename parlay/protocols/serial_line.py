from parlay.protocols.protocol import BaseProtocol
from parlay.server.broker import Broker
from twisted.internet import defer
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from parlay.endpoints.parlay_standard import ParlayCommandEndpoint, parlay_command, MSG_TYPES, BadStatusError
from parlay.protocols.utils import delay, timeout

class ASCIILineProtocol(BaseProtocol, LineReceiver):
    """
    When a client connects over a serial, this is the protocol that will handle the communication.
    The messages are encoded as a JSON string
    """

    broker = Broker.get_instance()

    @classmethod
    def open(cls, broker, port="/dev/tty.usbserial-FTAJOUB2", baudrate=57600, delimiter="\n"):
        """
        This will be called bvy the system to construct and open a new SSCOM_Serial protocol
        :param cls : The class object (supplied by system)
        :param broker:  current broker insatnce (supplied by system)
        :param port: the serial port device to use. On linux, something like/dev/ttyUSB0 on windows something like COM0
        """
        if isinstance(port, list):
            port = port[0]

        p = ASCIILineProtocol(port)
        SerialPort(p, port, broker._reactor, baudrate=115200)  # int(baudrate))

        return p

    @classmethod
    def get_open_params_defaults(cls):
        """Override the default implementation of 'get default open param' to return a list"""
        from serial.tools import list_ports
        # default impl
        defaults = BaseProtocol.get_open_params_defaults()

        potential_serials = [x[0] for x in list_ports.comports()]
        defaults['port'] = potential_serials
        defaults['baudrate'] = [9600, 57600]
        defaults['delimiter'] = "\n"

        return defaults

    def close(self):
        self.transport.loseConnection()
        return defer.succeed(None)  # fake deferred since we don't have anything asynchornous to do

    def __init__(self, port):
        BaseProtocol.__init__(self)
        self._parlay_name = port
        self.endpoints = [LineEndpoint(self._parlay_name, self._parlay_name, self)]

    def lineReceived(self, line):
        # only 1 endpoint
        self.endpoints[0].send_message(to="UI", contents={"DATA": line}, msg_type=MSG_TYPES.EVENT)



    def __str__(self):
        return "Serial Terminal @ " + self._parlay_name


class LineEndpoint(ParlayCommandEndpoint):

    def __init__(self, endpoint_id, name, protocol):
        ParlayCommandEndpoint.__init__(self, endpoint_id, name)
        self._protocol = protocol

    @parlay_command(async=True)
    def send_raw_data(self, data):
        self._protocol.sendLine(str(data))

    @defer.inlineCallbacks
    def wait_for_data(self, timeout_secs=3):
        while True:
            next_resp = yield timeout(self.wait_for_next_sent_msg(), timeout_secs)
            if next_resp["TOPICS"].get("MSG_TYPE", "") == MSG_TYPES.EVENT:
                    resp = next_resp["CONTENTS"]["DATA"]
                    defer.returnValue(resp)

