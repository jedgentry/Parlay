from base import BaseModule,ModuleMessage
import field

class CommandModule(BaseModule):


    #{"name":name,"id":id,"expected_payload_type":type}
    _commands = []

    def __init__(self, id, name):
        super(CommandModule,self).__init__(id, name)
        self._commands = self.__class__._commands

    def get_view_card(self):
        result = "<ul>"
        for c in self._commands:
            result += "<li>%d - %s</li>" % (c['id'], c['name'])
        result += "</ul>"




class CommandResponseAbstractMessage(ModuleMessage):
    payload =  field.Content(required=False)
    payload_type =field.Content(required=False)

class CommandMessage(CommandResponseAbstractMessage):
    name = "command"
    command = field.Content()

class ResponseMessage(CommandResponseAbstractMessage):
    name = "response"
    status = field.Content()