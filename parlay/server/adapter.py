from twisted.internet import reactor, defer
import sys

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

        self.open_protocols = []  # list of protocols that *ARE* open

    def publish(self, msg):
        """
        :type msg dict
        """
        raise NotImplementedError()

    def subscribe(self, fn, **kwargs):
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

    def get_protocols(self):
        """
        Return a list of protocols that could potentially be opened.
        Return a deferred if this is not ready yet
        """
        raise NotImplementedError()

    def discover(self, force):
        """
        Return the discovery (or a deferred) for all protocols and items attached to this adapter
        :type force bool
        :param force True if this requested discover action wants to clear any caches and do a fresh discover.
        """
        raise NotImplementedError()


class PyAdapter(Adapter):
    """
    Adapter for the Python Broker and Python environment
    """

    def __init__(self, broker):
        self._broker = broker
        self.protocols = []  # list of protocols that could potentially be opened
        self._discovery_cache = {}  # dict: K->V = Protocol -> discovery

        super(PyAdapter, self).__init__()

    def publish(self, msg):
        self._broker.publish(msg)

    def subscribe(self, fn, **kwargs):
        self._broker.subscribe(fn, **kwargs)

    def track_protocol(self, protocol):
        """
        track the given protocol for discovery
        """
        if protocol not in self.protocols:
            self.protocols.append(protocol)

    def untrack_protocol(self, protocol):
        """
        Untracks the given protocol. You must call this when a protocol has closed to clean up after it.
        """
        self._broker.unsubscribe_all(protocol)
        if protocol in self._broker._discovery_cache:
            del self._broker._discovery_cache[protocol]  # remove from discovery cache
        try:
            self.protocols.remove(protocol)
        except ValueError:
            pass

    def get_protocols(self):
        """
        Return a list of protocols that could potentially be opened
        """
        return self.protocols

    def discover(self, force):
        """
        Return the discovery (or a deferred) for all protocols and items attached to this adapter
        :type force bool
        :param force True if this requested discover action wants to clear any caches and do a fresh discover.
        """
        #clear the cache if we're told to force
        if force:
            self._discovery_cache = {}

        d_list = []
        for p in self.protocols:
            # if it's already in the cache, then just return it, otherwise, get it from the protocol
            if p in self._discovery_cache:
                d = defer.Deferred()
                d.callback(self._discovery_cache[p])
            else:
                d = defer.maybeDeferred(p.get_discovery)

            # add this protocols discovery
            def callback(disc, error=None, protocol=p):
                protocol_discovery = disc

                if error is not None:
                    protocol_discovery = {'error': str(error)}

                if type(disc) is dict:
                    # add it to the cache
                    self._discovery_cache[protocol] = protocol_discovery
                    return protocol_discovery
                else:
                    sys.stderr.write("ERROR: Discovery must return a dict, instead got: " + str(disc) +
                                     " from " + str(protocol))

            d.addCallback(callback)
            d.addErrback(lambda err: callback({}, error=err))

            d_list.append(d)

        # wait for all to be finished
        all_d = defer.gatherResults(d_list, consumeErrors=False)
        return all_d
