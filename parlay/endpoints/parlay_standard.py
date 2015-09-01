from base import BaseEndpoint
from parlay.protocols.utils import message_id_generator

class INPUT_TYPES(object):
    NUMBER ="NUMBER"
    STRING = "STRING"
    NUMBERS = "NUMBERS"
    STRINGS = "STRINGS"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
    DROPDOWN = "DROPDOWN"

class TX_TYPES(object):
    DIRECT = 'DIRECT'
    BROADCAST = "BROADCAST"

class MSG_TYPES(object):
    COMMAND = 'COMMAND'
    DATA = "DATA"
    EVENT = 'EVENT'
    RESPONSE = 'RESPONSE'

class MSG_STATUS(object):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"
    ACK = 'ACK'

class ParlayStandardEndpoint(BaseEndpoint):
    """
    This is a parlay standard endpoint. It supports building inputs for the UI in an intuitive manner during
    discovery. Inherit from it and use the parlay decorators to get UI functionality
    """

    def __init__(self, endpoint_id, name):
        # call parent
        BaseEndpoint.__init__(self, endpoint_id, name)
        self._content_fields = []
        self._topic_fields = []
        self._properties = {}  # Dictionary from name to (attr_name, read_only, write_only)
        self.endpoint_type = None
        self._msg_id_generator = message_id_generator(65535, 100) # default msg ids are 32 bit ints between 100 and 65535



    def create_field(self,  msg_key, input, label=None, required=False, hidden=False, default=None,
                  dropdown_options=None, dropdown_sub_fields=None):
        """
        Create a field for the UI
        """
        # make sure input is valid
        assert input in INPUT_TYPES.__dict__

        discovery = {"MSG_KEY": msg_key, "INPUT": input, "REQUIRED": required, "HIDDEN": hidden}

        if label is not None: discovery["LABEL"] = label
        if default is not None: discovery["DEFAULT"] = default
        if input == INPUT_TYPES.DROPDOWN:
            discovery["DROPDOWN_OPTIONS"] = dropdown_options
            discovery["DROPDOWN_SUB_FIELDS"] = dropdown_sub_fields

        return discovery

    def add_field(self,  msg_key, input, label=None, required=False, hidden=False, default=None,
                  dropdown_options=None, dropdown_sub_fields=None, topic_field=False):
        """
        Add a field to this endpoints discovery.
        This field will show up in the endpoint's CARD in the UI
        """

        discovery = self.create_field(msg_key, input, label, required, hidden, default, dropdown_options,
                                      dropdown_sub_fields)

        if topic_field:
            self._topic_fields.append(discovery)
        else:
            self._content_fields.append(discovery)

    def add_property(self, name, attr_name=None, input=INPUT_TYPES.STRING, read_only=False, write_only=False):
        """
        Add a property to this Endpointpoint.
        name : The name of the property
        attr_name = the name of the attr to set in 'self' when setting and getting (None if same as name)
        read_only = Read only
        write_only = write_only
        """
        attr_name = attr_name if attr_name is not None else name  # default
                                                # attr_name isn't needed for discovery, but for lookup
        self._properties[name] = {"NAME": name, "ATTR_NAME": attr_name, "INPUT": input,
                                  "READ_ONLY": read_only, "WRITE_ONLY": write_only}  # add to internal list



    def clear_fields(self):
        """
        clears all fields. Useful to change the discovery UI
        """
        del self._topic_fields[:]
        del self._content_fields[:]

    def get_discovery(self):
        """
        Discovery method. You can override this in a subclass if you want, but it will probably be easier to use the
        self.add_property and self.add_field helper methods and call this method like:
        def get_discovery(self):
            discovery = ParlayStandardEndpoint.get_discovery(self)
            # do other stuff for subclass here
            return discovery
        """

        #get from parent
        discovery = BaseEndpoint.get_discovery(self)
        discovery["TOPIC_FIELDS"] = self._topic_fields
        discovery["CONTENT_FIELDS"] = self._content_fields
        discovery["PROPERTIES"] = self._properties  # already formatted correctly.

        if self.endpoint_type is not None:
            discovery["TYPE"] = self.endpoint_type

        return discovery

    def send_message(self, to, from_=None, contents=None, tx_type=TX_TYPES.DIRECT, msg_type=MSG_TYPES.DATA, msg_id=None,
                     msg_status=MSG_STATUS.OK, response_req=False):
        """
        Sends a Parlay standard message.
        contents is a dictionary of contents to send
        """
        if msg_id is None:
            msg_id = self._msg_id_generator.next()
        if contents is None:
            contents = {}
        if from_ is None:
            from_ = self.endpoint_id

        msg = {"TOPICS": {"TO": to, "FROM": from_, "TX_TYPE": tx_type, "MSG_TYPE":msg_type, "MSG_ID": msg_id,
                          "MSG_STATUS": msg_status, "RESPONSE_REQ": response_req},
               "CONTENTS": contents}

        self._broker.publish(msg, self.on_message)

    def send_response(self, msg, contents=None, msg_status=MSG_STATUS.OK):
        if contents is None:
            contents = {}

        #swap to and from
        to, from_ = msg["TOPICS"]["FROM"], msg["TOPICS"]['TO']
        self.send_message(to, from_, tx_type=TX_TYPES.DIRECT, msg_type=MSG_TYPES.RESPONSE,
                          msg_id=msg["TOPICS"]["MSG_ID"], msg_status=msg_status, response_req=False,
                          contents=contents)


#TODO:
# make interfaces automatically add to discovery for the class that implemments them

def parlay_command(fn):
    fn._parlay_command = True
    return fn

class parlay_property(object):
    """
    A Property convenience class for ParlayCommandEndpoints.
    In the endpoint use like: self.prop = parlay_property()

    init_val : an inital value for the property
    val_type : the python type of the value. e.g. str, int, list, etc. The value will be coerced to this type on set
                and throw an exception if it couldn't be coerced
    read_only: Set to true to make read only
    write_only: Set to true to make write only
    """

    def __init__(self, init_val=None, val_type=None, read_only=False, write_only=True):
        self._val = init_val
        self._read_only = read_only
        self._write_only = write_only
        self._val_type = val_type
        # can't be both read and write only
        assert(not(self._read_only and write_only))


    def __get__(self, obj, objtype=None):
        return self._val

    def __set__(self, instance, value):
        self._val = value if self._val_type is None else self._val_type(value)



class ParlayCommandEndpoint(ParlayStandardEndpoint):
    """
    This is a parlay endpoint that takes commands, with values.
    If there is more than one command A dropdown will appear
    """

    def __init__(self, endpoint_id, name):
        # call parent
        ParlayStandardEndpoint.__init__(self, endpoint_id, name)
        self._commands = {}  # dict with command name -> callback function

        #add any function that have been decorated
        for member_name in [x for x in dir(self) if not x.startswith("__")]:
            member = getattr(self, member_name, {})
            # are we a method? and do we have the flag, and is it true?
            if callable(member) and hasattr(member, "_parlay_command") and member._parlay_command:
                self._commands[member_name] = member
                #build the sub-field based on their signature
                arg_names = member.func_code.co_varnames[1:]  # remove self
                # TODO: auto fill in required and defaults based on method signature
                member.__func__._parlay_sub_fields = [self.create_field(x, INPUT_TYPES.STRING) for x in arg_names]


    def get_discovery(self):
        """
        Will auto-populate the UI with inputs for commands
        """
        #start fresh
        self.clear_fields()
        self._add_commands_to_discovery()


        #call parent
        return ParlayStandardEndpoint.get_discovery(self)

    def _add_commands_to_discovery(self):
        """
        Add commands to the discovery for user input
        """

        if len(self._commands) == 0:
            return  # nothing to do here
        if len(self._commands) == 1:
            # If only one, then drop the dropdown option and have a hidden text option
            func_name=self._commands.keys()[0]
            func = self._commands[func_name]
            self.add_field("FUNC", INPUT_TYPES.STRING, default=func_name, hidden=True)
            #add the arguments as strait input fields
            self._content_fields.extend(func._parlay_sub_fields)

        else:  # more than 1 option
            command_names = self._commands.keys()
            command_names.sort()  # pretty-sort

            # add the command selection dropdown
            self.add_field("FUNC", INPUT_TYPES.DROPDOWN, label='command', default=command_names[0],
                           dropdown_options=[(x, x) for x in command_names],
                           dropdown_sub_fields=[self._commands[x]._parlay_sub_fields for x in command_names]
                           )

    def _add_properties_to_discovery(self):
        """
        Add properties to discovery
        """
        properties = []
        for member_name in [x for x in dir(self) if not x.startswith("__")]:
            member = getattr(self, member_name, {})
            if isinstance(member, parlay_property):
                properties.append(member_name)





    def on_message(self, msg):
        """
        Will handle command messages automatically.
        Returns True if the message was handled, False otherwise
        """
        topics, contents = msg["TOPICS"], msg["CONTENTS"]
        #handle property messages
        if topics.get("MSG_TYPE", "") == "PROPERTY":
            action = contents.get('ACTION', "")
            property_name = contents.get('PROPERTY', "")
            try:
                if action == 'SET':
                    assert 'VALUE' in contents  # we need a value to set!
                    setattr(self, self._properties[property_name], contents['VALUE'])
                    self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE"})
                    return True
                elif action == "GET":
                    val = getattr(self, self._properties[property_name])
                    self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE", "VALUE": val})
                    return True
            except Exception as e:
                self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE", "DESCRIPTION": str(e)},
                                   msg_status=MSG_STATUS.ERROR)



        #handle 'command' messages
        command = contents.get("FUNC", "")
        if command in self._commands:
            arg_names = ()
            try:
                method = self._commands[command]
                arg_names = method.func_code.co_varnames[1:]  # remove 'self'
                args = {k: msg["CONTENTS"][k] for k in arg_names}
                method(**args)

            except KeyError as e:
                # TODO: Reply with human readible error message for UI
                print("ERROR: missing args" + str(arg_names))

            return True
        else:
            return False


