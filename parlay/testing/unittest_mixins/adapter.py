"""
Adapter Mixin.  Use this mixin when doing unit tests to get access to a special unit test adapter that
will allow you check on publish and subscriptions
"""

from parlay.server import adapter
from twisted.internet import defer


class AdapterMixin(object):
    """
    Inherit from this Mixin to add a self.adapter that will let you hook in to
    publish and subscribe calls through self.adapter.published and self.adapter.subscribed
    """

    class AdapterImpl(adapter.Adapter):
        """
        The actual adapter implementation for this mixin
        """

        def __init__(self):
            # private
            self._items = []
            self._reactor = None
            self._connected = defer.Deferred()

            # public
            self.published = defer.Deferred()
            self.last_published = None  # the last message that was published
            self.subscribed = defer.Deferred()

            adapter.Adapter.__init__(self)

        def publish(self, msg, callback=None):
            """
            :type msg dict
            """
            temp = self.published
            self.published = defer.Deferred()
            temp.callback(msg)
            self.last_published = msg

        def subscribe(self, fn,  **kwargs):
            """
            :kwargs The topics and their values to subscribe to
            """
            temp = self.subscribed
            self.subscribed = defer.Deferred()
            temp.callback((fn, kwargs))

    adapter = AdapterImpl()
