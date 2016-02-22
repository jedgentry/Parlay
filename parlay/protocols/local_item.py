"""
The Local Item protocol lets you open arbitrary items that have been registered as local
"""

from base_protocol import BaseProtocol
from parlay.server.broker import Broker

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
        return cls

    return decorator


class LocalItemProtocol(BaseProtocol):
    ID = 0  # id counter for uniqueness

    @classmethod
    def open(cls, broker, item):
        item_class = LOCAL_ITEM_CLASSES[item]
        obj = item_class()
        return LocalItemProtocol(obj)

    @classmethod
    def get_open_params_defaults(cls):
        return {"Item": LOCAL_ITEM_CLASSES.keys()}

    @classmethod
    def close(cls):
        pass  # Don't need to do anything

    def __init__(self, item):
        BaseProtocol.__init__(self)
        self.items = [item]  # only 1
        self._unique_id = LocalItemProtocol.ID
        LocalItemProtocol.ID += 1

    def __str__(self):
        return "Local:" + str(self.items[0].__class__) + " # " + str(self._unique_id)


def auto_start():
    """
    Auto start local items that have that flag set
    """
    for name, cls in LOCAL_ITEM_CLASSES.iteritems():
        if cls._local_item_auto_connect:
            broker = Broker.get_instance()
            obj = LocalItemProtocol.open(broker, name)
            broker.protocols.append(obj)

# call this when the Broker is up and running
Broker.call_on_start(auto_start)
