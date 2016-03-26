"""
Protocol to connect parlay to an Anvil Cloud UI through anvil uplink
"""

from parlay.protocols.base_protocol import BaseProtocol
from parlay.items.parlay_standard import ParlayCommandItem
import anvil.server


class AnvilUplinkProtocol(BaseProtocol):
    """
    Protocol to connect parlay to an Anvil Cloud UI through anvil uplink
    """

    @classmethod
    def open(cls, broker, uplink_key):

        return AnvilUplinkProtocol(uplink_key)

    def __init__(self, uplink_key):
        self._uplink_key = uplink_key
        anvil.server.connect(uplink_key)
        super(AnvilUplinkProtocol, self).__init__()
        self._item = AnvilUplinkItem(item_id="Anvil Uplink", name="Anvil Uplink")
        anvil.server.register(self._item.sendCommand, "sendCommand")


class AnvilUplinkItem(ParlayCommandItem):
    """
    Item only used for convenience to send and receive messages. Also used to query status of the protocol
    """

    def sendCommand(self, item_id, command, **kwargs):
        handle = self.send_parlay_command(item_id, command, **kwargs)
        return handle.wait_for_complete()["CONTENTS"].get("RESULT", None)