from twisted.internet import reactor, defer

class Adapter(object):
    """
    Am Adapter is different from a normal parlay protocol. It is not meant to connect Parlay to an external system.
    It is only meant to connect an item to the broker and can not instantiated dynamically
    from the UI or scripts. It is tightly coupled to the item/broker and only supports publish/subscribe
    """

    def __init__(self):
        self._items = getattr(self, '_items', [])  # default to [] if a subclass hasn't set it
        self._reactor = getattr(self, 'reactor', reactor)
        self._connected = defer.Deferred()

    def publish(self, msg):
        """
        :type msg dict
        """
        raise NotImplementedError()

    def subscribe(self, **kwargs):
        """
        :kwargs The topics and their values to subscribe to
        """
        raise NotImplementedError()

    def register_item(self, item):
        """
        Register an item
        """
        self._items.append(item)
        #let the item know we're their adapter
        item._adapter = self