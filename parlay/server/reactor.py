"""
We've added a number of enhancments to the Twisted reactor to enable easier threading handling.
Instead of importing the twisted.internet reactor import this reactor like
from parlay.server.reactor import reactor
"""
from twisted.internet import reactor as twisted_reactor, defer
import thread as python_thread
from twisted.internet import threads as twisted_threads

class ReactorWrapper(object):
    def __init__(self, wrapped_reactor):
        self._reactor = wrapped_reactor
        self._thread = None

    def run(self, installSignalHandlers=True):
        self._thread = python_thread.get_ident()
        return self._reactor.run(installSignalHandlers=installSignalHandlers)

    def __getattr__(self, item):
        return getattr(self._reactor, item)

    def maybeblockingCallFromThread(self, callable, *args, **kwargs):
        """
        Call callable from the reactor thread.  If we are in the reactor thread, then call it and return a Deferred.
        If we are *not* in the reactor thread, then block on that deferred instal of returning it
        """
        current_thread = python_thread.get_ident()
        # if we're in the reactor thread
        if current_thread == self._thread:
            return defer.maybeDeferred(callable, *args, **kwargs)
        else:
            return twisted_threads.blockingCallFromThread(self._reactor, callable, *args, **kwargs)

    def maybeCallFromThread(self, callable, *args, **kwargs):
        """
        If we're in a separate thread from the reactor, then call from the reactor thread.
        If we're in the reactor thread, then schedule for call later in 0 seconds
        """
        current_thread = python_thread.get_ident()
        if current_thread == self._thread:
            self._reactor.callLater(0, callable, *args, **kwargs)
        else:
            self._reactor.callFromThread(callable, *args, **kwargs)



reactor = ReactorWrapper(twisted_reactor)