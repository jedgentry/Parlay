from parlay.server.broker import Broker
import field

class BaseModule(object):
    """
    The Base Module that all other modules should inherit from
    """

    def __init__(self, id, name):
        self.module_id = id
        self.module_name = name
        """:type Broker"""
        self._broker = Broker.get_instance()

        #subscribe onMessage to be called whenever we get a message *to* us
        self._broker.subscribe_listener(self.onMessage, to_id=id)



    def get_view_card(self):
        """
        Return an HTML viewcard for this module to use in the web-based UI
        """
        return "<span>#%d  - %s </span>" % (self.module_id, self.module_name)

    def onMessage(self, msg):
        """
        Every time we get a message for us, this method will be called with it.
        Be sure to override this.
        """
        raise NotImplementedError()



class InvalidMessageTypeDeclaration(Exception):
    """
    Raised when a message type has been declared that is invalid
    """
    pass

class InvalidMessage(Exception):
    """
    Raised when a message does not conform to it's type
    """
    pass


class MessageMeta(type):
    """
    Meta-Class that will keep track of *all* message types declared
    Also builds the message field lookups from the Django-model-style message class definitions
    """

    def __init__(cls,name,bases,dct):
        #register the message type
        if not hasattr(cls,'message_registry'):
            cls.message_registry= {}
        else:
            message_type_name = name if not hasattr(cls, 'name') else cls.name
            if message_type_name in cls.message_registry:
                raise InvalidMessageTypeDeclaration(message_type_name + " has already been declared. Please choose a different type name")

            cls.message_registry[message_type_name] = cls


        #add the fields to the cls
        cls._topic_fields = {}
        cls._content_fields = {}
        cls._fields = {}
        for field_name in dir(cls):
            #only pay attention to things that inherit from _FieldClass
            field_obj = getattr(cls, field_name)
            if isinstance(field_name, field._FieldClass):
                cls._fields[field_name] = field
                if isinstance(field_name, field.Topic):
                    cls._topic_fields[field_name] = field_obj
                else: #must be a content
                    cls._content_fields[field_name] = field_obj

        super(MessageMeta,cls).__init__(name,bases,dct)



class BaseMessage(object):
    """
    Base Message that all other messages need to inherit from.
    Has a list of topics and contents.  Topics can be subscribed to, contents can't
    Message of the form { "topics":{}, "contents":{}, "type":"MessageTypeName" }
    """

    __metaclass__ = MessageMeta

    def __init__(self, msg=None, **kwargs):
        """
        Override this in a subclass if you want to do something to the fields before init.
        (Don't forget to actually call it though)
        """
        self.msg = msg if msg is not None else {}

        for key, val in kwargs:
            setattr(self, key, val)




    @classmethod
    def from_message(cls, msg):
        """
        Builds a message object dict (to be passed to the ctor) from a dictionary of fields (JSON message)

        @param msg: A dictionary message that we will turn into an object
        @param obj: Used to Recursively go through each message type and append attributes


        TODO: This could me optimized by directly calling setattr() instead of building a dictionary and passing that
        to the BaseMessage constructor. This will only work if the subclass has not overwritten __init__
        This could be checked with "if cls.__init__ is BaseMessage.__init__"
        """
        result = {}
        #set all of the topics
        for topic, field_type in cls._topic_fields.iteritems():
            if topic not in msg['topics']:
                if field_type.required:
                    raise InvalidMessage("Message does not contain required topic: "+str(topic))
                else:
                    value = None
            else:
                value = msg['topics'][topic]

            #if the Field has a check() function, then call it
            if hasattr(field_type,'check'):
                value = field_type.check(value)

            #set the topic to the value
            result[topic] = value

        #set all of the contents
        for content, field_type in cls._content_fields.iteritems():
            if content not in msg['contents']:
                if field_type.required:
                    raise InvalidMessage("Message does not contain required content: "+str(content))
                else:
                    value = None
            else:
                value = msg['contents'][content]

            #if the Field has a check() function, then call it
            if hasattr(field_type,'check'):
                value = field_type.check(value)

            result[content] = value

        return cls(msg, **result)

    def to_message(self):
        """
        Return a dictionary message (easily serializable) for this object
        """
        #ensure that self.msg has the 'topic' and 'content' top levels
        if 'topics' not in self.msg: self.msg['topic'] = {}
        if 'contents' not in self.msg: self.msg['contents'] = {}

        #overwrite all of our fields in self.msg then return it
        #This means that any junk that has been manually added to self.msg will stick around (expected)
        for field_name, field_type in self.__class__._fields.iteritems():
            if isinstance(field_type, field.Topic):
                self.msg['topics'][field_name] = getattr(self, field_name, "")
            else: #must be content
                self.msg['contents'][field_name] = getattr(self, field_name, "")

        return self.msg



class SubscribeMessage(BaseMessage):

    #ironically, the topics field is a content field
    topics = field.Content()

class DiscoveryMessage(BaseMessage):

    type = field.Topic()

class ModuleMessage(BaseMessage):
    """
    Basic message that modules use to communicate with eachother
    has a to and a from field
    """

    from_id = field.Topic()
    to_id = field.Topic()



