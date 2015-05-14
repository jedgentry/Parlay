


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



class Protocol(object):
    __metaclass__ = ProtocolMeta


    def get_modules(self):
        """
        Returns a deferred that will callback (or errback) with a list of discovered devices
        """
        raise NotImplementedError()


