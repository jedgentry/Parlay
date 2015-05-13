
from parlay.modules.base import BaseMessage, InvalidMessage

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

        super(ProtocolMeta,cls).__init__(name,bases,dct)



class Protocol(object):
    __metaclass__ = ProtocolMeta

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def processMessage(self, msg):
        """
        Call this with a dictionary type message once the protocol has parsed it
        """
        try:
            msg_class = BaseMessage.message_registry[msg['type']]
            msg_obj = msg_class.from_message(msg)
            self.dispatcher.call_listeners(msg_obj)
        except KeyError as e:
            raise InvalidMessage("No/bad message type in msg "+str(msg))

    def get_modules(self):
        """
        Returns a deferred that will callback (or errback) with a list of discovered devices
        """
        raise NotImplementedError()