from parlay.server.broker import Broker


class BaseEndpoint(object):
    """
    The Base Endpoint that all other Endpoint should inherit from
    """


    def __init__(self, endpoint_id, name):
        self.endpoint_id = endpoint_id
        self.endpoint_name = name
        """:type Broker"""
        self._broker = Broker.get_instance()
        self.children = [] #child endpoints

        # subscribe on_message to be called whenever we get a message *to* us
        self._broker.subscribe(self.on_message, TO=endpoint_id)
        self._broker.subscribe(self.on_sent_message, FROM=endpoint_id)
        self._interfaces = [] #list of interfaces we support

    def on_message(self, msg):
        """
        Every time we get a message for us, this method will be called with it.
        Be sure to override this.
        """
        pass

    def on_sent_message(self, msg):
        """
        any time there is a message SENT by us, this method will be called with it
        """
        pass
    def get_discovery(self):
        """
        The protocol can call this to get discovery from me
        """
        discovery = {"NAME": self.endpoint_name, "ID": self.endpoint_id, "TYPE": self.get_endpoint_template_string(),
                     "INTERFACES": self._interfaces, "CHILDREN": [x.get_discovery() for x in self.children]}
                     # TODO: have interfaces automatically build in here
        return discovery


    def get_endpoint_template_string(self):
        """
        This returns the type string for the endpoint eg: sscom/STD_ENDPOINT "
        """
        templates = []
        for cls in (self.__class__, ) + self.__class__.__bases__:
            name = cls.TEMPLATE_NAME if hasattr(cls, "TEMPLATE_NAME") else cls.__name__
            templates.append(name)

        return "/".join(templates)


