"""
Define the base Protocol classes and meta-classes.

For documentation on broker and common message types see parlay.protocols::
"""


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

    protocol_registry = {}

    def __init__(cls, name, bases, dct):
        # register the message type

        protocol_name = name if not hasattr(cls, 'name') else cls.name
        cls._protocol_type_name = protocol_name
        if protocol_name in ProtocolMeta.protocol_registry:
            raise InvalidProtocolDeclaration(protocol_name + " has already been declared." +
                                             "Please choose a different protocol name")

        ProtocolMeta.protocol_registry[protocol_name] = cls

        super(ProtocolMeta, cls).__init__(name, bases, dct)


