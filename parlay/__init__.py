

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
    Open a protocol immediately after the Broker initializes.

    :param protocol_name: name of protocol class to call the open method
    :param kwargs: keyword arguments to pass to the protocol's _open_ method
    :return: none
    """
    Broker.call_on_start(lambda: Broker.get_instance().open_protocol(protocol_name, kwargs))
