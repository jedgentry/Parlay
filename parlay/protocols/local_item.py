"""
The Local Item protocol lets you open arbitrary items that have been registered as local
"""

from base_protocol import BaseProtocol, BrokerProtocol
from parlay.server.broker import Broker
from functools import wraps

LOCAL_ITEM_CLASSES = {}


def local_item(auto_connect=False):
    """
    A class decorator that registers a class as independent.

    :param auto_connect: whether to automatically connect to the Parlay broker when the item is created.
    :return: decorator function
    """
    def decorator(cls):
        # register class with dict of local items
        class_name = cls.__name__
        cls._local_item_auto_connect = auto_connect  # set the auto connect flag
        LOCAL_ITEM_CLASSES[class_name] = cls
        # override __init__
        orig_init = cls.__init__

        @wraps(orig_init)
        def new_init(self, *args, **kwargs):
            """
            Call the original ctor and then pass self to a new local protocol and append it to the broker
            """
            result = orig_init(self, *args, **kwargs)
            broker = Broker.get_instance()
            protocol_obj = LocalItemProtocol(self)
            broker.track_protocol(protocol_obj)
            return result
        cls.__init__ = new_init
        return cls

    return decorator


class LocalItemProtocol(BaseProtocol, BrokerProtocol):
    ID = 0  # id counter for uniqueness

    class TransportStub(object):
        """
        Fake transport that will allow the protocol to think its writing to a transport
        """
        def __init__(self):
            self._broker = Broker.get_instance()

        def write(self, payload):
            self._broker.publish(payload)

    @classmethod
    def open(cls, broker, item_name):
        item_class = LOCAL_ITEM_CLASSES[item_name]
        obj = item_class()
        return LocalItemProtocol(obj)

    @classmethod
    def open_for_obj(cls, item_obj):
        broker = Broker.get_instance()
        protocol_obj = LocalItemProtocol(item_obj)
        broker.track_protocol(protocol_obj)
        return protocol_obj

    @classmethod
    def get_open_params_defaults(cls):
        return {"item": LOCAL_ITEM_CLASSES.keys()}

    @classmethod
    def close(cls):
        pass  # Don't need to do anything

    def __init__(self, item):
        BaseProtocol.__init__(self)
        self.items = [item]  # only 1
        self._unique_id = LocalItemProtocol.ID
        self._broker = Broker.get_instance()
        LocalItemProtocol.ID += 1

    def publish(self, msg):
        self._broker.publish(msg)

    def subscribe(self, fn, **kwargs):
        self._broker.subscribe(fn=fn, **kwargs)

    def __str__(self):
        return "Local:" + str(self.items[0].__class__) + " # " + str(self._unique_id)

auto_started_items = []

def auto_start():
    """
    Auto start local items that have that flag set
    """
    for name, cls in LOCAL_ITEM_CLASSES.iteritems():
        if cls._local_item_auto_connect:
            #construct them on init and store them in the list so they don't get garbage collected
            auto_started_items.append(cls())

# call this when the Broker is up and running
Broker.call_on_start(auto_start)
