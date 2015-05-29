


class InvalidProtocolDeclaration(Exception):
    """
    Raised when there was a problem with your protocol declaration
    """
    pass

class ProtocolMeta(type):
    """
    Meta-Class that will keep track of *all* message types declared
    Also builds the message field lookups from the Django-model-style message class definitions
    """

    def __init__(cls,name,bases,dct):
        #register the message type
        if not hasattr(cls,'message_registry'):
            cls.protocol_registry= {}
        else:
            protocol_name = name if not hasattr(cls, 'name') else cls.name
            if protocol_name in cls.protocol_registry:
                raise InvalidProtocolDeclaration(protocol_name + " has already been declared. Please choose a different protocol name")

            cls.protocol_registry[protocol_name] = cls

        super(ProtocolMeta, cls).__init__(name, bases, dct)



class BaseProtocol(object):
    __metaclass__ = ProtocolMeta


    @classmethod
    def open(cls, broker):
        """
        Override this with a generic method that will open the protocol.
        The first argument must be the broker, the rest will be parameters that the user can set. Default arguments will
        be sent to the UI and can be overwritten bu the user
        It must return the built protocol (subclass of Protocol)  that will be registered with the Broker
        Be sure to decorate it with @classmethod

        e.g.
        @classmethod
        def open(cls, broker, ip, port=8080):
            return protocol(ip,port)
        """
        raise NotImplementedError()

    def get_modules(self):
        """
        Returns a deferred that will callback (or errback) with a list of discovered devices
        """
        raise NotImplementedError()


