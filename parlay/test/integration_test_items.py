from twisted.internet import defer

from parlay.items.parlay_standard import ParlayCommandItem
from parlay import parlay_command, local_item
from parlay.server.broker import run_in_thread

from parlay.testing.integrationtest import TestCase, unittest


class CommandTestToBrokerOverWebsocket(TestCase):

    def test_local_commands(self):
        local_adder = LocalAdder("LocalAdder", "LocalAdder")

        result = local_adder.add(2, 3)
        self.assertEqual(result, 5)

        result = local_adder.add_async(2, 3)
        self.assertEqual(result, 5)

    def test_remote_commands(self):
        local_adder = LocalAdder("LocalAdder", "LocalAdder")
        remote_adder = RemoteAdder("RemoteAdder", "RemoteAdder")
        remote_adder_disc = RemoteAdderWithDiscovery("RemoteAdderDisc", "RemoteAdderDisc", "LocalAdder")

        result = remote_adder.add(2, 3, "LocalAdder")
        self.assertEqual(result, 5)

        result = remote_adder.add_async(2, 3, "LocalAdder")
        self.assertEqual(result, 5)

        result = remote_adder_disc.add(2, 3)
        self.assertEqual(result, 5)

        result = remote_adder_disc.add_async(2, 3)
        self.assertEqual(result, 5)


@local_item()
class LocalAdder(ParlayCommandItem):
    """
    Helper class to test custom commands
    """

    @parlay_command()
    def add(self, x, y):
        return x + y

    @parlay_command(async=True)
    def add_async(self, x, y):
        return x + y


@local_item()
class RemoteAdder(ParlayCommandItem):
    @parlay_command()
    def add(self, x, y, to):
        cmd = self.send_parlay_command(to, "add", _timeout=2, x=x, y=y)
        return cmd.wait_for_complete()

    @parlay_command(async=True)
    def add_async(self, x, y, to):
        cmd = self.send_parlay_command(to, "add", _timeout=2, x=x, y=y)
        result = yield cmd.wait_for_complete()
        defer.returnValue(result)


@local_item()
class RemoteAdderWithDiscovery(ParlayCommandItem):

    def __init__(self, item_id, name, remote_id):
        self.discovered = False
        self.remote_id = remote_id
        ParlayCommandItem.__init__(self, item_id=item_id, name=name)

    @run_in_thread
    def _check_discovered(self):
        if not self.discovered:
            self.discover()
            self.remote_item = self.get_item_by_id(self.remote_id)
            self.discovered = True

    @parlay_command()
    def add(self, x, y):
        self._check_discovered()
        return self.remote_item.add(x, y)

    @parlay_command(async=True)
    def add_async(self, x, y):
        yield self._check_discovered()
        result = yield self.remote_item.add(x, y)
        defer.returnValue(result)


if __name__ == "__main__":
    unittest.main()
