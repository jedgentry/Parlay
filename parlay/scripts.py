
from parlay.utils import scripting_setup

# public API
setup = scripting_setup.setup

subscribe = lambda fn, **kwargs: scripting_setup.script.subscribe(fn, **kwargs)
discover = lambda force=True: scripting_setup.script.discover(force)
get_item_by_name = lambda item_name: scripting_setup.script.get_item_by_name(item_name)
get_item_by_id = lambda item_id: scripting_setup.script.get_item_by_id(item_id)
sleep = lambda time: scripting_setup.script.sleep(time)
shutdown_broker = lambda: scripting_setup.script.shutdown_broker()

open = lambda protocol_name, **kwargs: scripting_setup.script.open(protocol_name, **kwargs)
open_protocol = open
close_protocol = lambda protocol_id: scripting_setup.script.close_protocol(protocol_id)
call_later = lambda seconds, func, *args, **kwargs: scripting_setup.script.call_later(seconds, func, *args, **kwargs)

# send_parlay_command = lambda *args, **kwargs: scripting_setup.script.


