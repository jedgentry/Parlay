from parlay.server.broker import Broker

class INPUT_TYPES(object):
    NUMBER ="NUMBER"
    STRING = "STRING"
    NUMBERS = "NUMBERS"
    STRINGS = "STRINGS"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
    DROPDOWN = "DROPDOWN"

#lookup table for arg discovery
INPUT_TYPE_DISCOVERY_LOOKUP = {'str': INPUT_TYPES.STRING, 'string': INPUT_TYPES.STRING, 'char': INPUT_TYPES.STRING,
                               'int': INPUT_TYPES.NUMBER, 'float': INPUT_TYPES.NUMBER, 'double': INPUT_TYPES.NUMBER,
                               'short': INPUT_TYPES.NUMBER, 'long': INPUT_TYPES.NUMBER, 'list[]': INPUT_TYPES.ARRAY}

#dynamically add list types
for k in INPUT_TYPE_DISCOVERY_LOOKUP.keys():
    v = INPUT_TYPE_DISCOVERY_LOOKUP[k]
    list_type = INPUT_TYPES.ARRAY
    if v == INPUT_TYPES.NUMBER:
        list_type = INPUT_TYPES.NUMBERS
    elif v == INPUT_TYPES.STRING:
        list_type = INPUT_TYPES.STRINGS
    INPUT_TYPE_DISCOVERY_LOOKUP['list['+k+']'] = list_type

#lookup table for arg conversion
INPUT_TYPE_CONVERTER_LOOKUP = {'int': int, 'str': str, 'string': str, 'char': chr, 'float': float, 'double': float,
                      'short' : int, 'long': int, 'list[]': lambda list_arg: list_arg}
# dynamically add list types
for k in INPUT_TYPE_CONVERTER_LOOKUP.keys():
    v = INPUT_TYPE_CONVERTER_LOOKUP[k]
    INPUT_TYPE_CONVERTER_LOOKUP['list['+k+']'] = lambda list_arg, k=k, v=v: [v(x) for x in list_arg]


class TX_TYPES(object):
    DIRECT = 'DIRECT'
    BROADCAST = "BROADCAST"

class MSG_TYPES(object):
    COMMAND = 'COMMAND'
    DATA = "DATA"
    EVENT = 'EVENT'
    RESPONSE = 'RESPONSE'
    PROPERTY = 'PROPERTY'
    STREAM = 'STREAM'

class MSG_STATUS(object):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"
    ACK = 'ACK'

class BaseEndpoint(object):
    """
    The Base Endpoint that all other Endpoint should inherit from
    """


    def __init__(self, endpoint_id, name):
        self.endpoint_id = endpoint_id
        self.endpoint_name = name
        """:type Broker"""
        self._broker = Broker.get_instance()
        self.children = [] #child endpoints

        # subscribe on_message to be called whenever we get a message *to* us
        self._broker.subscribe(self.on_message, TO=endpoint_id)
        self._broker.subscribe(self.on_sent_message, FROM=endpoint_id)
        self._interfaces = [] #list of interfaces we support

    def on_message(self, msg):
        """
        Every time we get a message for us, this method will be called with it.
        Be sure to override this.
        """
        pass

    def on_sent_message(self, msg):
        """
        any time there is a message SENT by us, this method will be called with it
        """
        pass
    def get_discovery(self):
        """
        The protocol can call this to get discovery from me
        """
        discovery = {"NAME": self.endpoint_name, "ID": self.endpoint_id, "TYPE": self.get_endpoint_template_string(),
                     "INTERFACES": self._interfaces, "CHILDREN": [x.get_discovery() for x in self.children]}
                     # TODO: have interfaces automatically build in here
        return discovery


    def get_endpoint_template_string(self):
        """
        This returns the type string for the endpoint eg: sscom/STD_ENDPOINT "
        """
        templates = []
        for cls in [self.__class__, ] + get_recursive_base_list(self.__class__):
            name = cls.TEMPLATE_NAME if hasattr(cls, "TEMPLATE_NAME") else cls.__name__
            templates.append(name)

        return "/".join(templates)


def get_recursive_base_list(cls, list=None):
    """
    Get the full class heirarchy list for a class, to see *all* classes and super classes a python class inherits from
    """
    if list is None:
        list = []

    for base in cls.__bases__:
        list.append(base)
        get_recursive_base_list(base, list)

    return list

from twisted.internet import reactor
from autobahn.twisted.websocket import  WebSocketClientProtocol, WebSocketClientFactory

"""def connect_endpoint(endpoint_class, host='localhost', reactor=reactor):
    \"""
    Connect an endpoint up to the the broker at 'host' . Use the reactor reactor
    :param endpoint_class : the class of the endpoint to instantiate and use
    :param host The broker to connect to
    :param reactor The reactor to use for this endpoint's event loop
    \"""
    #connect it up
    factory = WebSocketClientFactory("ws://" + engine_ip + ":" + str(engine_port))
    factory.protocol = script_class
    reactor.connectTCP(engine_ip, engine_port, factory)

    if not reactor.running:
        reactor.run()
"""