import termios
import json
from twisted.internet import defer, fdesc
from twisted.internet.abstract import FileDescriptor
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from parlay.server.adapter import Adapter
from parlay.server.broker import Broker


class FileTransport(FileDescriptor):
    """
    Implements FileDescriptor abstract class with a simple file descriptor.
    Surprisingly, this is not included in Twisted.

    Based heavily on twisted.internet.serialport.SerialPort
    """

    def __init__(self, protocol, filename, reactor=None):
        FileDescriptor.__init__(self, reactor)
        self.filename = filename
        self._f = open(filename, 'r+')
        fdesc.setNonBlocking(self._f)
        self.flushInput()
        self.flushOutput()
        self.protocol = protocol
        self.protocol.makeConnection(self)
        self.startReading()
        self.connected = 1

    def __del__(self):
        self._f.close()

    def writeSomeData(self, data):
        return fdesc.writeToFD(self.fileno(), data)

    def doRead(self):
        return fdesc.readFromFD(self.fileno(), self.protocol.dataReceived)

    def fileno(self):
        return self._f.fileno()

    def flushInput(self):
        """Clear input buffer, discarding all that is in the buffer."""
        termios.tcflush(self._f.fileno(), termios.TCIFLUSH)

    def flushOutput(self):
        """Clear output buffer, aborting the current output and
        discarding all that is in the buffer."""
        termios.tcflush(self._f.fileno(), termios.TCOFLUSH)


class LineTransportServerAdapter(Adapter, LineReceiver):
    """
    Adapter class to connect the Parlay broker to a device (for example, serial)
    that implements the L{ITransport} interface.
    """

    broker = Broker.get_instance()
    DEFAULT_DISCOVERY_TIMEOUT_TIME = 10

    def __init__(self, transport_factory, delimiter='\n', **kwargs):
        """
        Creates an instance of ParlayOverLineTransportServerAdapter
        :param transport_factory: Transport class that must implement FileDescriptor interface
        :param delimiter: delimiter character that separates lines (default=newline)
        :param kwargs: optional keyword arguments to pass to transport_factory
        :return:
        """
        self._discovery_response_defer = None
        self.reactor = self.broker.reactor
        self.delimiter = str(delimiter).decode("string_escape")
        self.transport = transport_factory(self, **kwargs)
        self._cached_discovery = None
        self.discovery_timeout_time = self.DEFAULT_DISCOVERY_TIMEOUT_TIME
        Adapter.__init__(self)

    def get_protocols(self):
        return []

    def get_open_protocols(self):
        return []

    def lineReceived(self, line):
        """
        Handle a delimited line of bytes received by the transport.
        :param line:
        :return: None
        """
        msg = json.loads(line)

        # if we're waiting for discovery and the message is a discovery response
        if self._discovery_response_defer is not None and \
                msg['TOPICS'].get('type', None) == 'get_protocol_discovery_response':
            discovery = msg['CONTENTS'].get('discovery', [])
            self._cached_discovery = discovery
            self._discovery_response_defer.callback(discovery)
            self._discovery_response_defer = None

        # else it's just a regular message, publish it
        else:
            self.broker.publish(msg, self.send_message_as_json)

    def discover(self, force):
        """
        Sends a Parlay message of 'get_protocol_discovery' type via the transport.
        :param force: if False, return cached discovery if available.
        :type force: bool
        :return: Deferred to wait for discovery response
        """

        # if already in the middle of discovery
        if self._discovery_response_defer is not None:
            return self._discovery_response_defer

        if not force and self._cached_discovery is not None:
            return self._cached_discovery

        self._discovery_response_defer = defer.Deferred()
        self.send_message_as_json({'TOPICS': {'type': 'get_protocol_discovery'}, 'CONTENTS': {}})

        def timeout():
            if self._discovery_response_defer is not None:
                # call back with nothing if timeout
                self._discovery_response_defer.callback({})
                self._discovery_response_defer = None

        self.reactor.callLater(self.discovery_timeout_time, timeout)
        return self._discovery_response_defer

    def send_message_as_json(self, msg):
        """
        Transforms parlay message dictionary to JSON, adds delimiting character,
        and sends it over the transport.
        :param msg:
        :return:
        """
        self.sendLine(json.dumps(msg))


class FileDeviceServerAdapter(LineTransportServerAdapter):
    """
    This adapter is designed for communication ports that present themselves
    as regular device files, that CANNOT be opened as serial ports.  Instead,
    we use the FileTransport transport layer and read/write them as regular files.

    An example is the g_serial driver for Linux, whose device file cannot
    be opened by twisted.internet.serialport.SerialPort, but can be opened with
    the standard python open() function.

    **Example Usage**::

        from parlay import Broker, start

        device_adapter = FileDeviceServerAdapter('/dev/ttyGS0')

        broker = Broker.get_instance()
        broker.adapters.append(device_adapter)
        start()

    """

    def __init__(self, filename, delimiter='\n'):
        LineTransportServerAdapter.__init__(self, FileTransport, delimiter=delimiter, filename=filename)


class SerialServerAdapter(LineTransportServerAdapter):
    """
    This class defines a Parlay server adapter for a serial port.

    This class would be used when the Parlay broker will be running locally,
    and there is some device speaking the Parlay message protocol on the other
    side of a serial port.  This adapter will allow that other device to connect
    to the Parlay broker.

    **Example Usage**::

        from parlay import Broker, start

        serial_adapter = SerialServerAdapter('/dev/ttyUSB0', baudrate=57600)

        broker = Broker.get_instance()
        broker.adapters.append(serial_adapter)
        start()

    """
    def __init__(self, port, baudrate=115200, delimiter='\n'):
        LineTransportServerAdapter.__init__(self, SerialPort,
                                            delimiter=delimiter,
                                            port=port,
                                            baudrate=baudrate)
