from parlay.server.broker import Broker
from collections import Iterable

class INPUT_TYPES(object):
    NUMBER ="NUMBER"
    STRING = "STRING"
    NUMBERS = "NUMBERS"
    STRINGS = "STRINGS"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
    DROPDOWN = "DROPDOWN"

# lookup table for arg discovery
INPUT_TYPE_DISCOVERY_LOOKUP = {'str': INPUT_TYPES.STRING, 'string': INPUT_TYPES.STRING, 'char': INPUT_TYPES.STRING,
                               'int': INPUT_TYPES.NUMBER, 'float': INPUT_TYPES.NUMBER, 'double': INPUT_TYPES.NUMBER,
                               'short': INPUT_TYPES.NUMBER, 'long': INPUT_TYPES.NUMBER, 'list': INPUT_TYPES.ARRAY}

# dynamically add list types
for k in INPUT_TYPE_DISCOVERY_LOOKUP.keys():
    v = INPUT_TYPE_DISCOVERY_LOOKUP[k]
    list_type = INPUT_TYPES.ARRAY
    if v == INPUT_TYPES.NUMBER:
        list_type = INPUT_TYPES.NUMBERS
    elif v == INPUT_TYPES.STRING:
        list_type = INPUT_TYPES.STRINGS
    INPUT_TYPE_DISCOVERY_LOOKUP['list['+k+']'] = list_type

# lookup table for arg conversion
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
    PROGRESS = 'PROGRESS'


class BaseItem(object):
    """
    The Base Item that all other Items should inherit from
    """

    def __init__(self, item_id, name, adapter=None, parents=None):
        self.item_id = item_id
        self.item_name = name
        """:type Adapter"""  # use the default pyadapter if no specific adapter was chosen
        self._adapter = adapter if adapter is not None else Broker.get_instance().pyadapter

        self.children = set()  # Initialize children set

        parents = set() if not parents else parents  # Create a set to represent the parents of the item
        self.parents = {parents} if not isinstance(parents, Iterable) else set(parents)  # Make sure parents is iterable
        self._add_self_as_child_to_parents()

        # subscribe on_message to be called whenever we get a message *to* us
        self.subscribe(self.on_message, TO=item_id)
        self._interfaces = []  # list of interfaces we support

    def subscribe(self, _fn, **kwargs):
        self._adapter.subscribe(_fn, **kwargs)

    def publish(self, msg):
        self._adapter.publish(msg)

    def on_message(self, msg):
        """
        Every time we get a message for us, this method will be called with it.
        Be sure to override this.
        """
        pass

    def get_discovery(self):
        """
        The protocol can call this to get discovery from me
        """
        # TODO: have interfaces automatically build in here
        discovery = {"NAME": self.item_name, "ID": self.item_id, "TYPE": self.get_item_template_string(),
                     "INTERFACES": self._interfaces, "CHILDREN": [x.get_discovery() for x in self.children]}

        return discovery

    def get_item_template_string(self):
        """
        This returns the type string for the item eg: sscom/STD_ITEM "
        """
        templates = []
        for cls in [self.__class__, ] + get_recursive_base_list(self.__class__):
            name = cls.TEMPLATE_NAME if hasattr(cls, "TEMPLATE_NAME") else cls.__name__
            templates.append(name)

        return "/".join(templates)

    def _add_self_as_child_to_parents(self):
        """
        Adds this BaseItem instance as a child to the parents passed as parameters in the constructor.
        :return: None
        """
        try:
            for parent in set(self.parents):
                parent.add_child(self)
        except Exception as e:
            print "Unable to add this item as a child. Make sure parent is a Parlay item that supports " \
                  "adding children."
            print "Exception: ", str(e)
            raise e

    def add_child(self, child):
        """
        Adds child to the children list of our item. NOTE: duplicates are not permitted.

        Child should be an instance of a class that is derived from BaseItem.

        :param child: BaseItem to add
        :return:
        """
        # Make sure child has not already been added
        if not isinstance(child, BaseItem):
            print "add_child() error. Child provided was not an instance of BaseItem."
            return

        self.children.add(child)
        child.parents.add(self)

    def is_child(self):
        """
        Determines if this item is a child of another item. Or in other words this Item has a parent.
        :return: boolean - True if this item is a child, False if not.
        """
        return len(self.parents) != 0

    def __del__(self):
        self._adapter.deregister_item(self)


def get_recursive_base_list(cls, base_list=None):
    """
    Get the full class heirarchy list for a class, to see *all* classes and super classes a python class inherits from
    """
    if base_list is None:
        base_list = []

    for base in cls.__bases__:
        base_list.append(base)
        get_recursive_base_list(base, base_list)

    return base_list

from twisted.internet import reactor
from autobahn.twisted.websocket import  WebSocketClientProtocol, WebSocketClientFactory
