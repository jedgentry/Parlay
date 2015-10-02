"""
The Local Endpoint protocol lets you open arbitrary endpoints that have been registered as local
"""

from protocol import BaseProtocol
from parlay.server.broker import Broker

LOCAL_ENDPOINT_CLASSES = {}

def local_endpoint(auto_connect=False):
    """
    A class decorator that registers a class as independent
    """
    def decorator(cls):
        #register it
        class_name = cls.__name__
        cls._local_endpoint_auto_connect = auto_connect  # set the auto connect flag
        LOCAL_ENDPOINT_CLASSES[class_name] = cls
        return cls

    return decorator


class LocalEndpointProtocol(BaseProtocol):

    @classmethod
    def open(cls, broker, Endpoint):
        endpoint_class = LOCAL_ENDPOINT_CLASSES[Endpoint]
        obj = endpoint_class()
        return LocalEndpointProtocol(obj)

    @classmethod
    def get_open_params_defaults(cls):
        return {"Endpoint": LOCAL_ENDPOINT_CLASSES.keys()}

    @classmethod
    def close(self):
        pass  # Don't need to do anything


    def __init__(self, endpoint):
        BaseProtocol.__init__(self)
        self.endpoints = [endpoint]  # only 1


    def __str__(self):
        return "Local:" + str(self.endpoints[0].__class__)


def auto_start():
    """
    Auto start local endpoints that have that flag set
    """
    for name, cls in LOCAL_ENDPOINT_CLASSES.iteritems():
        if cls._local_endpoint_auto_connect:
            broker = Broker.get_instance()
            obj = LocalEndpointProtocol.open(broker, name)
            broker.protocols.append(obj)

#call this when the Broker is up and running
Broker.call_on_start(auto_start)