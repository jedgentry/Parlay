
from parlay.server.reactor import ReactorWrapper, twisted_reactor, python_thread


class ReactorImpl(ReactorWrapper):

    def __init__(self):
        ReactorWrapper.__init__(self, twisted_reactor)
        self._thread = python_thread.get_ident()  # the current thread is the reactor thread
        self.running = True  # we're always running

class ReactorMixin(object):
    """
    Inherit this class to get a self.reactor class that willa ct like a real reactor but give hooks for unit testing
    """

    reactor = ReactorImpl()