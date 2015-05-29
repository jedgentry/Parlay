from base import BaseModule, ModuleMessage
import field


class CommandModule(BaseModule):
    # {"name": name, "id": id, "expected_payload_type": type}
    _commands = []

    def __init__(self, module_id, name):
        super(CommandModule, self).__init__(module_id, name)
        self._commands = self.__class__._commands

    def on_message(self, msg):
        pass


class CommandResponseAbstractMessage(ModuleMessage):
    payload = field.Content(required=False)
    payload_type = field.Content(required=False)


class CommandMessage(CommandResponseAbstractMessage):
    name = "command"
    command = field.Content()


class ResponseMessage(CommandResponseAbstractMessage):
    name = "response"
    status = field.Content()
