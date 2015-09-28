"""
The Independent Endpoint protocol lets you open arbitrary endpoints that have been registered as independent
"""

from protocol import BaseProtocol
INDEPENDENT_ENDPOINT_CLASSES = {}

def independent_endpoint(cls):
    """
    A class decorator that registeres a class as independent
    """
    #register it
    class_name = cls.__name__
    INDEPENDENT_ENDPOINT_CLASSES[class_name] = cls
    return cls


class IndependentEndpointProtocol(BaseProtocol):

    @classmethod
    def open(cls, broker, Endpoint):
        endpoint_class = INDEPENDENT_ENDPOINT_CLASSES[Endpoint]
        obj = endpoint_class()
        return IndependentEndpointProtocol(obj)

    @classmethod
    def get_open_params_defaults(cls):
        return {"Endpoint": INDEPENDENT_ENDPOINT_CLASSES.keys()}

    @classmethod
    def close(self):
        pass  # Don't need to do anything


    def __init__(self, endpoint):
        BaseProtocol.__init__(self)
        self.endpoints = [endpoint]  # only 1


    def __str__(self):
        return "IndependentEndpoint:" + str(self.endpoints[0].__class__)
