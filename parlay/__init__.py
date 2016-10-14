__version__ = '0.3.10'


# Item Public API
from parlay.items.parlay_standard import ParlayCommandItem, ParlayProperty, parlay_command, ParlayDatastream
from parlay.protocols.local_item import local_item

# Script Public API
from utils.parlay_script import ParlayScript


from server.broker import Broker

# Broker public API
Modes = Broker.Modes
start = Broker.start
start_for_test = Broker.start_for_test
stop = Broker.stop
stop_for_test = Broker.stop_for_test


def open_protocol(protocol_name, **kwargs):
    """
    Sets up a protocol to be opened after the Broker initializes.

    This function has the same effect as opening a new protocol from the
    browser-based user interface.

    :param protocol_name: name of protocol class to call the open method
    :type protocol_name: str
    :param kwargs: keyword arguments to pass to the protocol's _open_ method
    :return: none


    **Example Usage**::

        from parlay import open_protocol, start
        open_protocol("ASCIILineProtocol", port="/dev/ttyUSB0", baudrate=57600)
        start()

    """
    return Broker.call_on_start(lambda: Broker.get_instance().open_protocol(protocol_name, kwargs))


class WidgetsImpl(object):
    """
    Stub that will warn users that accidentally import or try to use widgets that it can only be used in the UI
    """

    def __getitem__(self, item):
        raise NotImplementedError("widgets can only be used from the Parlay UI")

    def __setitem__(self, key, value):
        raise NotImplementedError("widgets can only be used from the Parlay UI")

widgets = WidgetsImpl()