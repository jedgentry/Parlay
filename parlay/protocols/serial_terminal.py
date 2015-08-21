from parlay.protocols.protocol import BaseProtocol
from parlay.server.broker import Broker
from twisted.internet import defer
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver

class SerialTerminal(BaseProtocol, LineReceiver):
    """
    When a client connects over a websocket, this is the protocol that will handle the communication.
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

        SerialTerminal.delimiter = '\n'#delimiter
        p = SerialTerminal(port)
        SerialPort(p, port, broker._reactor, baudrate=9600)  # int(baudrate))

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
        self._parlay_name = port
        self.broker.subscribe(self.onParlayMsg, TO=self._parlay_name)


    def onParlayMsg(self, msg):
        self.sendLine(str(msg['CONTENTS']['data']))

    def lineReceived(self, line):
        msg = {"TOPICS": {"TO": "UI", "TX_TYPE": "DIRECT", "MSG_TYPE": "DATA", "FROM": self._parlay_name},
               "CONTENTS": {"DATA": line}}
        self.broker.publish(msg, self.onParlayMsg)

    def get_discovery(self):
        return [{
            "NAME": self._parlay_name,
            "ID": self._parlay_name,
            "TEMPLATE": "STD_ENDPOINT",
            "INTERFACES": [],
            "CONTENT_FIELDS": [{"MSG_KEY": "data", "INPUT": "STRING"}]
        }]

    def __str__(self):
        return "Serial Terminal @ " + self._parlay_name
