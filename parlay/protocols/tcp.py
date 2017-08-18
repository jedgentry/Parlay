from twisted.internet.defer import succeed
from twisted.internet.protocol import Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from parlay.protocols.base_protocol import BaseProtocol
from parlay.items.parlay_standard import ParlayCommandItem, parlay_command
from parlay.utils.reporting import log_stack_on_error


class TCPClientProtocol(BaseProtocol, Protocol):

    class _TCPStates(object):
        DISCONNECTED = 0
        IN_PROGRESS = 1
        CONNECTED = 2

    def __init__(self, adapter, ip, port):

        self._adapter = adapter
        self._ip = ip
        self._port = port
        self._state = self._TCPStates.DISCONNECTED
        self._deferred = None

        if getattr(self, "items", None) is None:
            item_id = "TCP-{}:{}".format(ip, port)
            item = TCPClientItem(item_id, item_id, protocol=self)
            self.items = [item]

        BaseProtocol.__init__(self)

    @classmethod
    def open(cls, adapter, ip, port):
        """
        Open a TCP Protocol.  This does not actually make the TCP connection to the
        target IP address and port.  That will be done when there is data to send.

        :param adapter: Parlay adapter
        :param ip: target IP address (example "192.168.0.2")
        :type ip: str
        :param port: target TCP port
        :type port: int
        :return: the protocol object
        """
        port = int(port)
        p = cls(adapter, ip, port)
        return p

    @classmethod
    def get_open_params_defaults(cls):
        """
        Gives the default arguments for the open() parameters.
        :return: The dictionary containing the default arguments.
        """
        defaults = BaseProtocol.get_open_params_defaults()
        defaults['port'] = [8888]
        defaults['ip'] = ['127.0.0.1']
        return defaults

    def connectionLost(self, reason=None):
        """ Called when the underlying TCP connection is lost. """
        self._state = self._TCPStates.DISCONNECTED
        if self._deferred is not None:
            self._deferred.cancel()
            self._deferred = None

    def connectionMade(self):
        """ Called when the underlying TCP connection is made. """
        self.transport.setTcpNoDelay(True)
        self._state = self._TCPStates.CONNECTED
        self._deferred = None

    def close(self):
        if self._state != self._TCPStates.DISCONNECTED:
            self.transport.loseConnection()
        if self._state == self._TCPStates.IN_PROGRESS:
            self._deferred.cancel()

    def dataReceived(self, data):
        """
        Called with a chunk of raw bytes from the underlying TCP stream.

        Override this method if you want to process raw bytes before sending them to the
        attached Parlay items.  For example, you could buffer the raw data and look for a
        delimiting character to separate the raw bytes into messages.

        :param data: raw bytes received by the TCP stream
        :type data: str
        :return: None
        """
        for item in self.items:
            item.raw_data_received(data)

    def send_raw_data(self, data):
        """
        Send raw bytes over the TCP connection.  If the TCP connection is not currently
        open, open it, then send the data when it is open.

        Note that even with an active connection, sending data may not happen immediately.
        The OS-level TCP stack may buffer data to consolidate into more efficient IP packets.
        If this is an issue, you may need to disable Nagle's algorithm,
        via `self.transport.setTcpNoDelay(True)`.

        :param data: raw bytes to send
        :type data: str
        :return: None
        """
        if self._state == self._TCPStates.CONNECTED:
            self.transport.write(data)
            return succeed(None)

        elif self._state == self._TCPStates.IN_PROGRESS:
            self._deferred.addCallback(lambda _: self.transport.write(data))

        elif self._state == self._TCPStates.DISCONNECTED:
            self._state = self._TCPStates.IN_PROGRESS
            d = self.connect(self._adapter, self._ip, self._port)
            d.addCallback(lambda _: self.transport.write(data))
            d.addErrback(self.connect_failed)
            self._deferred = log_stack_on_error(d)

        return self._deferred

    def connect(self, adapter, ip, port):
        """ Establish a new TCP connection and link it with this protocol. """

        endpoint = TCP4ClientEndpoint(adapter.reactor, ip, port)
        d = connectProtocol(endpoint, self)

        def bad_connection(failure):
            message = "Could not connect to {}:{}\n {}\n".format(ip, port, failure.getErrorMessage())
            raise IOError(message)

        d.addErrback(bad_connection)
        return d

    def connect_failed(self, failure):
        self.connectionLost()
        return failure


class TCPClientItem(ParlayCommandItem):

    def __init__(self, item_id, item_name, protocol):
        self._protocol = protocol
        ParlayCommandItem.__init__(self, item_id, item_name)

    def raw_data_received(self, data):
        """
        Override this method to deal with data incoming from the TCP stream.
        :param data: chunk of raw bytes received
        :return: None
        """
        pass

    @parlay_command(async=True)
    def send_raw_data(self, data):
        """
        Send raw bytes over the TCP connection.
        :param data: raw bytes to send
        :type data: str
        :return: None
        """
        return self._protocol.send_raw_data(data)
