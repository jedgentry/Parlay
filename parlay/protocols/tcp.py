from twisted.internet.protocol import Protocol, Factory
from twisted.internet.endpoints import TCP4ClientEndpoint
from parlay.protocols.base_protocol import BaseProtocol
from parlay.items.parlay_standard import ParlayCommandItem, parlay_command


class TCPClientProtocol(BaseProtocol, Protocol):

    def __init__(self, item_id=None, item_name=None):
        """
        By default, this protocol constructs a single Parlay Item with a optionally provided id and name.
        Override this method if you wish to construct or register an item in a different way.
        """
        BaseProtocol.__init__(self)

        id_or_name = "com.promenade.common.tcpprotocol.1"
        if item_id is None:
            item_id = id_or_name
        if item_name is None:
            item_name = id_or_name

        item = TCPClientItem(item_name, item_id, protocol=self)
        self.items = [item]

    @classmethod
    def open(cls, adapter, ip, port):
        """
        Open a TCP
        :param adapter: Parlay adapter
        :param ip: target IP address (example "192.168.0.2")
        :type ip: str
        :param port: target TCP port
        :type port: int
        :return: Deferred that will fire with protocol created after TCP connection is established
        """
        port = int(port)

        # Twisted expects protocols to have factories
        factory = Factory()
        factory.protocol = cls

        endpoint = TCP4ClientEndpoint(adapter.reactor, ip, port)
        deferred = endpoint.connect(factory)
        return deferred

    def close(self):
        self.transport.loseConnection()

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
        Send raw bytes over the TCP connection.

        Note that this may not happen immediately.  The OS-level TCP stack may buffer data
        to consolidate into more efficient IP packets.  If this is an issue, you may need
        to disable Nagle's algorithm, via `self.transport.setTcpNoDelay(True)`.

        :param data: raw bytes to send
        :type data: str
        :return: None
        """
        self.transport.write(data)


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
        raise NotImplementedError()

    @parlay_command()
    def send_raw_data(self, data):
        """
        Send raw bytes over the TCP connection.
        :param data: raw bytes to send
        :type data: str
        :return: None
        """
        self._protocol.send_raw_data(data)
