from parlay.server.broker import Broker


class BaseModule(object):
    """
    The Base Module that all other modules should inherit from
    """

    def __init__(self, module_id, name):
        self.module_id = module_id
        self.module_name = name
        """:type Broker"""
        self._broker = Broker.get_instance()

        # subscribe on_message to be called whenever we get a message *to* us
        self._broker.subscribe_listener(self.on_message, self, to=module_id)

    def on_message(self, msg):
        """
        Every time we get a message for us, this method will be called with it.
        Be sure to override this.
        """
        raise NotImplementedError("{} must implement the on_message function".format(type(self)))

    def get_id(self):
        return self.module_id

    def get_name(self):
        return self.module_name

