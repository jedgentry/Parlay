
from parlay.server.reactor import ReactorWrapper, twisted_reactor, python_thread
from parlay.server.broker import Broker

class ReactorImpl(ReactorWrapper):

    def __init__(self):
        ReactorWrapper.__init__(self, twisted_reactor)
        self._thread = python_thread.get_ident()  # the current thread is the reactor thread
        self.running = True  # we're always running




_reactor_stub = ReactorImpl()
#make sure the Broker is using US as the reactor
Broker.get_instance().reactor = _reactor_stub

class ReactorMixin(object):
    """
    Inherit this class to get a self.reactor class that willa ct like a real reactor but give hooks for unit testing
    """

    reactor = _reactor_stub