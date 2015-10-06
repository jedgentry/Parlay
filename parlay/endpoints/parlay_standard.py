import functools
from base import BaseEndpoint
from parlay.protocols.utils import message_id_generator
from twisted.internet import defer, threads
from parlay.server.broker import Broker
from twisted.internet.task import LoopingCall


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
    PROPERTY = 'PROPERTY'
    STREAM = 'STREAM'

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
        self._datastreams = {}
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

    def add_datastream(self, name, attr_name=None, units=""):
        """
        Add a property to this Endpointpoint.
        name : The name of the property
        attr_name = the name of the attr to set in 'self' when setting and getting (None if same as name)
        read_only = Read only
        write_only = write_only
        """
        attr_name = attr_name if attr_name is not None else name  # default
                                                # attr_name isn't needed for discovery, but for lookup
        self._datastreams[name] = {"NAME": name, "ATTR_NAME": attr_name, "UNITS": units}  # add to internal list



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
        discovery["PROPERTIES"] = [x for x in self._properties.values()]  # already formatted correctly.
        discovery["DATASTREAMS"] = [x for x in self._datastreams.values()]  # already .formatted correctly.

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

        msg = {"TOPICS": {"TO": to, "FROM": from_, "TX_TYPE": tx_type, "MSG_TYPE": msg_type, "MSG_ID": msg_id,
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

    def send_parlay_command(self, to, command_name, **kwargs):
        contents = kwargs
        contents['FUNC'] = command_name
        msg_id = self._msg_id_generator.next()
        self.send_message(to, contents=contents, response_req=True, msg_id=msg_id)

        d = defer.Deferred()
        def listener(msg):
            d.callback(msg["CONTENTS"])
            #unscubscribe
            self._broker._reactor.callLater(0,
                                            lambda: self._broker.unsubscribe(self,
                                                                             {"TO": self.endpoint_id, "MSG_ID": msg_id}))


        self._broker.subscribe(listener, self, TO=self.endpoint_id, MSG_ID=msg_id)
        return d


from parlay.scripts.parlay_script import ENDPOINT_PROXIES


def parlay_command(async=False):
    """
    Make the decorated method a parlay_command.

    :param: async: If True, will run as a normal twisted async function call. If False, parlay will spawn a separate
    thread and run the function synchronously (Default false)
    """

    def decorator(fn):
        if async:  # trivial wrapper
            wrapper = fn
        else:  # run this command synchronously in a separate thread
            wrapper = functools.wraps(fn)(lambda self, *args, **kwargs: threads.deferToThread(fn, self, *args, **kwargs))

        wrapper._parlay_command = True
        wrapper._parlay_fn = fn  # in case it gets wrapped again, this is the actual function so we can pull kwarg names
        return wrapper

    return decorator

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

class parlay_datastream(object):
    """
    A DataStream convenience class for ParlayCommandEndpoints.
    In the endpoint use like: self.prop = parlay_datastream()
    Datastream are read-only values that alert listeners  at a certain frequency

    init_val : an inital value for the property
    val_type : the python type of the value. e.g. str, int, list, etc. The value will be coerced to this type on set
                and throw an exception if it couldn't be coerced
    read_only: Set to true to make read only
    write_only: Set to true to make write only
    """

    def __init__(self, init_val=None, units=""):
        self._val = init_val
        self.listeners = {}  # key->value requester -> repeater
        self.units = units
        self.broker = Broker.get_instance()

    def __get__(self, obj, objtype=None):
        return self._val

    def __set__(self, instance, value):
        self._val = value

    def stream(self, requester_id, looper, hz):
        current_looper = self.listeners.get(requester_id, None)
        if current_looper is not None and current_looper.running:
            current_looper.stop()
        if hz > 0:
            self.listeners[requester_id] = looper
            looper.start(1/hz)


class BadStatusError(Exception):
    """
    Throw this if you want to return a Bad Status!
    """
    def __init__(self, error, description=""):
        self.error = error
        self.description = description

class ParlayCommandEndpoint(ParlayStandardEndpoint):
    """
    This is a parlay endpoint that takes commands, with values.
    If there is more than one command A dropdown will appear
    """

    def __init__(self, endpoint_id, name):
        # call parent
        ParlayStandardEndpoint.__init__(self, endpoint_id, name)
        self._commands = {}  # dict with command name -> callback function

        #ease of use deferred for wait* functions
        self._wait_for_next_sent_message = defer.Deferred()
        self._wait_for_next_recv_message = defer.Deferred()

        self._broker.subscribe(self._wait_for_next_recv_msg_subscriber, TO=self.endpoint_id)
        self._broker.subscribe(self._wait_for_next_sent_msg_subscriber, FROM=self.endpoint_id)

        #add any function that have been decorated
        for member_name in [x for x in dir(self) if not x.startswith("__")]:
            member = getattr(self, member_name, {})
            # are we a method? and do we have the flag, and is it true?
            if callable(member) and hasattr(member, "_parlay_command") and member._parlay_command:
                self._commands[member_name] = member
                #build the sub-field based on their signature
                arg_names = member._parlay_fn.func_code.co_varnames[1:member._parlay_fn.func_code.co_argcount]   # remove self
                # TODO: auto fill in required and defaults based on method signature
                member.__func__._parlay_sub_fields = [self.create_field(x, INPUT_TYPES.STRING) for x in arg_names]

        #run discovery to init everything for a first time
        #call it immediately after init
        self._broker._reactor.callLater(0, ParlayCommandEndpoint.get_discovery, self)


    def get_discovery(self):
        """
        Will auto-populate the UI with inputs for commands
        """
        #start fresh
        self.clear_fields()
        self._add_commands_to_discovery()
        self._add_properties_to_discovery()
        self._add_datastreams_to_discovery()

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
        #clear properties
        self._properties = {}
        for member_name in [x for x in dir(self) if not x.startswith("__")]:
            member = getattr(self, member_name, {})
            if isinstance(member, parlay_property):
                self.add_property(member_name, member_name, INPUT_TYPES.STRING,
                                  read_only=member._read_only, write_only=member._write_only)

    def _add_datastreams_to_discovery(self):
        """
        Add properties to discovery
        """
        #clear properties
        self._datastreams = {}
        for member_name in [x for x in dir(self) if not x.startswith("__")]:
            member = getattr(self, member_name, {})
            if isinstance(member, parlay_datastream):
                self.add_datastream(member_name, member_name, member.units)





    def on_message(self, msg):
        """
        Will handle command messages automatically.
        Returns True if the message was handled, False otherwise
        """
        topics, contents = msg["TOPICS"], msg["CONTENTS"]
        msg_type = topics.get("MSG_TYPE", "")
        #handle property messages
        if msg_type == "PROPERTY":
            action = contents.get('ACTION', "")
            property_name = contents.get('PROPERTY', "")
            try:
                if action == 'SET':
                    assert 'VALUE' in contents  # we need a value to set!
                    prop = getattr(self, self._properties[property_name]["ATTR_NAME"])
                    prop._val = contents['VALUE']
                    self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE"})
                    return True
                elif action == "GET":
                    val = getattr(self, self._properties[property_name]["ATTR_NAME"])
                    self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE", "VALUE": val})
                    return True
            except Exception as e:
                self.send_response(msg, {"PROPERTY": property_name, "ACTION": "RESPONSE", "DESCRIPTION": str(e)},
                                   msg_status=MSG_STATUS.ERROR)


        #handle data stream messages
        if msg_type == "STREAM":
            try:
                stream_name = contents["STREAM"]
                hz = float(contents["RATE"])
                requester = topics["FROM"]
                def sample():
                    val = getattr(self, self._datastreams[stream_name]["ATTR_NAME"])._val
                    self.send_message(to=requester, msg_type=MSG_TYPES.STREAM, contents={'VALUE': val})

                looper = LoopingCall(sample)
                self.__dict__[stream_name].stream(requester, looper, hz)

            except Exception as e:
                self.send_response(msg, {"PROPERTY": stream_name, "ACTION": "RESPONSE", "DESCRIPTION": str(e)},
                                   msg_status=MSG_STATUS.ERROR)
        #handle 'command' messages
        command = contents.get("FUNC", "")
        if command in self._commands:
            arg_names = ()
            try:
                method = self._commands[command]
                arg_names = method._parlay_fn.func_code.co_varnames[1:method._parlay_fn.func_code.co_argcount]  # remove 'self'
                kws = {k: msg["CONTENTS"][k] for k in arg_names}
                # try to run the method, return the data and say status ok
                def run_command():
                    return method(**kws)

                result = defer.maybeDeferred(run_command)
                result.addCallback(lambda r: self.send_response(msg, {"RESULT": r}))
                def bad_status_errback(f):
                    #is this an exppliti bad status?
                    if isinstance(f.value, BadStatusError):
                        error = f.value
                        self.send_response(msg, contents={"DESCRIPTION": error.description, "ERROR": error.error},
                                           msg_status=MSG_STATUS.ERROR)
                    #or is it unknown generic exception?
                    else:
                        self.send_response(msg, contents={"DESCRIPTION": f.getErrorMessage(), "TRACEBACK": f.getTraceback()},
                                           msg_status=MSG_STATUS.ERROR)

                #if we get an error, then return it
                result.addErrback(bad_status_errback)

            except KeyError as e:
                # TODO: Reply with human readible error message for UI
                print("ERROR: missing args" + str(arg_names))

            return True
        else:
            return False




    def _wait_for_next_sent_msg_subscriber(self, msg):
        d = self._wait_for_next_sent_message
        #set up new one before calling callback in case things triggered by the callback need to wait for the next sent
        self._wait_for_next_sent_message = defer.Deferred()
        d.callback(msg)

    def _wait_for_next_recv_msg_subscriber(self, msg):
        d = self._wait_for_next_recv_message
        #set up new one before calling callback in case things triggered by the callback need to wait for the next sent
        self._wait_for_next_recv_message = defer.Deferred()
        d.callback(msg)

    def wait_for_next_sent_msg(self):
        """
        Returns a deferred that will callback on the next message we SEND
        """
        return self._wait_for_next_sent_message

    def wait_for_next_recv_msg(self):
        """
        Returns a deferred that will callback on the next message we RECEIVE
        """
        return self._wait_for_next_recv_message




class ParlayStandardScriptProxy(object):
    """
    A proxy class for the script to use, that will auto-detect discovery information and allow script writers to
    intuitively use the endpoint
    """

    class PropertyProxy(object):
        """
        Proxy class for a parlay property
        """

        def __init__(self, name, endpoint_proxy, blocking_set=True):
            self._name = name
            self._endpoint_proxy = endpoint_proxy
            # do we want to block on a set until we get the ACK?
            self._blocking_set = blocking_set

        def __get__(self, instance, owner):
            msg = instance._script.make_msg(instance.name, None, msg_type=MSG_TYPES.PROPERTY,
                                            direct=True, response_req=True, PROPERTY=self._name, ACTION="GET")
            resp = instance._script.send_parlay_message(msg)
            #reutn the VALUE of the response
            return resp["CONTENTS"]["VALUE"]

        def __set__(self, instance, value):
            msg = instance._script.make_msg(instance.name, None, msg_type=MSG_TYPES.PROPERTY,
                                            direct=True, response_req=self._blocking_set,
                                            PROPERTY=self._name, ACTION="SET", VALUE=value)
            #Wait until we're sure its set
            resp = instance._script.send_parlay_message(msg)

        def __str__(self):
            return str(self.__get__(self._endpoint_proxy, self._endpoint_proxy))


    class StreamProxy(object):
        """
        Proxy class for a parlay stream
        """
        def __init__(self, name, endpoint_proxy, rate):
            self._name = name
            self._endpoint_proxy = endpoint_proxy
            self._val = None
            self._rate = rate

            msg = endpoint_proxy._script.make_msg(endpoint_proxy.name, None, msg_type=MSG_TYPES.STREAM,
                                            direct=True, response_req=True, STREAM=self._name, RATE=rate)
            endpoint_proxy._script.send_parlay_message(msg)

        def _update_val_listener(self, msg):
            """
            Script listener that will update the val whenever we get a stream update
            """
            topics, contents = msg["TOPICS"], msg['CONTENTS']
            if topics.get("MSG_TYPE", "") == MSG_TYPES.STREAM and contents.get("STREAM", "") == self._name \
                    and 'VALUE' in contents:
                self._val = contents["VALUE"]
            return False  # never eat me!

        def __get__(self, instance, owner):
            return self._val

        def __set__(self, instance, value):
            raise NotImplementedError()  # you can't set a STREAM



    def __init__(self, discovery, script):
        """
        discovery: The discovery dictionary for the endpoint that we're proxying
        script: The script object we're running in
        """
        self.name = discovery["NAME"]
        self.endpoint_id = discovery["ID"]
        self._discovery = discovery
        self._script = script

        # look at the discovery and add all commands, properties, and streams

        # commands
        func_dict = next(iter([x for x in discovery['CONTENT_FIELDS'] if x['MSG_KEY'] == 'FUNC']), None)
        if func_dict is not None:  # if we have commands
            command_names = [x[0] for x in func_dict["DROPDOWN_OPTIONS"]]
            command_args = [x for x in func_dict["DROPDOWN_SUB_FIELDS"]]
            for i in range(len(command_names)):
                func_name = command_names[i]
                arg_names = [x['MSG_KEY'] for x in command_args[i]]
                def _closure_wrapper(func_name=func_name, arg_names=arg_names):
                    def func(*args, **kwargs):
                        #ad positional args with name lookup
                        for j in range(len(args)):
                            kwargs[arg_names[j]] = args[j]

                        # check args
                        for name in arg_names:
                            if name not in kwargs:
                                raise TypeError("Missing argument: "+name)

                        #send the message and block for response
                        msg = self._script.make_msg(self.name, func_name, msg_type=MSG_TYPES.COMMAND,
                                                direct=True, response_req=True, FUNC=func_name, **kwargs)
                        resp = self._script.send_parlay_message(msg)
                        return resp['CONTENTS']['RESULT']

                    # set this object's function to be that function
                    setattr(self, func_name, func)
                #need this trickery so closures work in a loop
                _closure_wrapper()

        #properties
        for prop in discovery.get("PROPERTIES", []):
            setattr(self, prop['NAME'], ParlayStandardScriptProxy.PropertyProxy(prop['NAME'], self))

        #stream
        for stream in discovery.get("STREAMS", []):
            setattr(self, stream['NAME'], ParlayStandardScriptProxy.StreamProxy(stream['NAME'], self, 0))


ENDPOINT_PROXIES['ParlayStandardEndpoint'] = ParlayStandardScriptProxy
ENDPOINT_PROXIES['ParlayCommandEndpoint'] =  ParlayStandardScriptProxy





