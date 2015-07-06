"""
Define the base Protocol classes and meta-classes.

For documentation on broker and common message types see parlay.protocols::
"""
import inspect


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

    def __init__(cls, name, bases, dct):
        #register the message type
        if not hasattr(cls, 'protocol_registry'):
            cls.protocol_registry = {}
        else:
            protocol_name = name if not hasattr(cls, 'name') else cls.name
            if protocol_name in cls.protocol_registry:
                raise InvalidProtocolDeclaration(protocol_name + " has already been declared." +
                                                 "Please choose a different protocol name")

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

    @classmethod
    def get_open_params(cls):
        """
        Returns the params for the cls.open() class method. Feel free to overwrite this in a sub-class if this default
        implementation doesn't fit your protocol's needs.
        :return: A list of parameter names
        :rtype: list
        """
        # get the arguments
        # (don't use argspec because it is needlesly strict and fails on perfectly valid Cython functions)
        args, varargs, varkw = inspect.getargs(cls.open.func_code)
        return args[2:]  # remove 'cls' and 'broker'

    @classmethod
    def get_open_params_defaults(cls):
        """
        return the defaults for parameters to the cls.open() using inspect. Feel free to overwrite this in a sub-class if this default
        implementation doesn't fit your protocol's needs.
        :return: A dictionary of parameter names -> default values.
        :rtype: dict
        """
        # (don't use argspec because it is needlesly strict and fails on perfectly valid Cython functions)
        defaults = cls.open.func_defaults if cls.open.func_defaults is not None else []
        params = cls.get_open_params()
        # cut params to only the last x (defaults are always at the end of the signature)
        params = params[len(params) - len(defaults):]
        return dict(zip(params, defaults))

    def get_discovery(self):
        """
        This will get called when a discovery message is sent out. Return a deferred that will be called back with
        all attached:
        endpoint types, message types, and connected endpoint instances
        """
        raise NotImplementedError()


