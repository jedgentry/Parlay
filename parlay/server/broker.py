"""

The broker is the main message router of the parlay system. The broker uses a standard publish/subscribe paradigm.
Modules that want to send message 'publish' the message to the broker and the broker sends a copy of that message to
 every connection that has 'subscribed' to messages with a matching topic signature. For more information on message types
 and structures.

 All messages must be key-value pairs (typically JSON strings or python dictionaries). The only requirement for messages
 is that every message must have, at its top level, a 'topics' key and a 'CONTENTS' key. 'topics' must be a key value pairing
 and can be subscribed to. 'CONTENTS' can be an object of any type and can **not** be subscribed to.

 Any message that isn't a 'special type' is implicitly a command to 'publish' that message.

 There are two 'special type' messages that are *not* published. The are distinguished by the 'type' topic.
 * 'type': 'broker' messages  are special commands to the broker. These messages and their foramt is defined on the protocol
  documentation page

 * 'type': 'subscribe' messages are a command to the broker to subscribe to a specific combination of topics. The 'CONTENTS'
 in a subscribe message must be simply the key 'TOPICS' and a key-value pair of TOPICS/values to subscribe to.
 e.g. :  (in JSON) {'TOPICS':{'type':'subscribe'},'CONTENTS':{'TOPICS':{'to':'Motor 1', 'id': 12345} } }
"""
from twisted.internet import reactor, defer, ssl
from parlay.protocols.protocol import BaseProtocol

from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS
from twisted.application import internet, service
from twisted.web import static, server
import os
import json

# path to the root parlay folder
PARLAY_PATH = os.path.dirname(os.path.realpath(__file__)) + "/.."
BROKER_DIR = os.path.dirname(os.path.realpath(__file__))

class Broker(object):
    """
    The Dispatcher is the sole holder of global state. There should be only one.
    It also coordinates all communication between protcols
    """
    instance = None

    # discovery info for the broker
    _discovery = {'TEMPLATE': 'Broker', 'NAME': 'Broker', "ID": "__Broker__", "interfaces": ['broker'],
                  "CHILDREN": []}

    class Modes:
        """
        These are the modes that the broker can run in.
        * Development mode is purposefully easy to use an insecure to allow logging and
        easy control of the parlay system
        * Production mode is locked down and *more* secure (Security should always be
        validated independently)
        """
        DEVELOPMENT = "DEVELOPER_MODE"
        PRODUCTION = "PRODUCTION_MODE"


    def __init__(self, reactor, websocket_port=8085, http_port=8080, https_port=8081, secure_websocket_port=8086):
        assert(Broker.instance is None)

        #the currently connected protocols
        self.protocols = []

        #The listeners that will be called whenever a message is received
        self._listeners = {}  # See Listener lookup document for more info

        self._reactor = reactor

        #THERE CAN BE ONLY ONE
        Broker.instance = self

        self.websocket_port = websocket_port
        self.http_port = http_port
        self.https_port = https_port
        self.secure_websocket_port = secure_websocket_port

    @staticmethod
    def get_instance():
        """
        @rtype Broker
        """
        if Broker.instance is None:
            Broker.instance = Broker(reactor)

        return Broker.instance


    def publish(self, msg, write_method):
        """
        Publish a message to the Parlay system
        :param msg : The message to publish
        :param write_method : the protocol's method to callback if the broker needs to send a response
        """
        topic_type = msg['TOPICS'].get('type', None)
        #handle broker and subscribe messages special
        if topic_type == 'broker':
            self.handle_broker_message(msg, write_method)
        elif topic_type == 'subscribe':
            self.handle_subscribe_message(msg, write_method)
        elif topic_type == 'unsubscribe':
            self.handle_unsubscribe_message(msg, write_method)
        #generic publish for all other messages
        else:
            self._publish(msg)

    def _publish(self, msg, root_list=None):
        """
        Call all of the listeners that match msg

        Time Complexity is O(2*n) * O(k)
        where:  n = the number of levels of the listener list
                k = the number of keys in the msg

        TODO: Remake this in super-fast Cython as a Trie
        """
        if root_list is None: root_list = self._listeners
        #call any functions in the None key
        for func, owner in root_list.get(None, []):
            func(msg)

        TOPICS = msg['TOPICS']
        #for each key in the listeners list
        for k in TOPICS.keys():
            #if the key exists and  values match, then call any functions
            #or look further
                                  # root_list[k] is the value, which is a key to another dictionary
                                 #The None key in that dictionary will contain a list of funcs to call
                                # (Any other key will lead to yet another dictionary of keys and values)
            if k in root_list and TOPICS[k] in root_list[k]:
                #recurse
                self._publish(msg, root_list[k][TOPICS[k]])


    def subscribe(self, func, **kwargs):
        """
        Register a listener. The kwargs is a dictionary of args that **all** must be true
        to call this listener. You may register the same function multiple times with different
        kwargs, and it may be called multiple times for each message.
        @param func: The function to run
        @param kwargs: The key/value pairs to listen for
        """
        # only bound methods are allowed to subscribe so they are easier to clean up later
        if hasattr(func, 'im_self') and func.im_self is not None:
            owner = func.im_self
        else:
            raise ValueError("Function {} passed to subscribe_listener() ".format(func.__name__) +
                             "must be a bound method of an object")

        #sort so we always get the same order
        keys = sorted(kwargs.keys())
        root_list = self._listeners
        for k in keys:
            v = kwargs[k]

            if k not in root_list:
                root_list[k] = {}
            if v not in root_list[k]:
                root_list[k][v] = {}
            #go down a level
            root_list = root_list[k][v]

        #now that we're done, we have the leaf in root_list. Append it to the None list
        listeners = root_list.get(None, [])
        listeners.append((func, owner))
        root_list[None] = listeners

    def unsubscribe(self, owner, TOPICS):
        """
        unsubscribe owner from all subscriptions that match TOPICS. Only EXACT matches will be unsubscribed
        """

        keys = sorted(TOPICS.keys())
        root_list = self._listeners

        #go down the trie
        for k in keys:
            v = TOPICS[k]

            if k not in root_list:
                return  # not subscribed
            if v not in root_list[k]:
                return  # not subscribed
            #go down a level
            root_list = root_list[k][v]

        #now that we're done, that means that we are subscribed and we have the leaf in root_list.
        listeners = root_list.get(None, [])
        #filter out any subscriptions by 'owner'
        root_list[None] = [x for x in listeners if x.owner != owner]


    def _clean_trie(self, root_list=None):
        """
        Internal method called to clean out the trie from subscription keys that no longer have any subscriptions
        :param root_list : sub-trie to clean, or None for root of trie
        :result : number of subscriptions in the sub-trie
        """

        # base case
        if root_list is None:
            root_list = self._listeners

        #total subscriptions in this subtrie
        total_sub = 0
        for k in root_list.keys():
            if k is not None:  # skip the special NONE key (that's used for callback list)
                for v in root_list[k].keys():
                    num_sub = self._clean_trie(root_list[k][v])
                    # remove a sub-trie if it doesn't have any subscriptions in it
                    if num_sub == 0:
                        del root_list[k][v]
                    else:  # our total_sub is the sum of our subtries + any subscriptions at our level
                        total_sub += num_sub
            # delete the k if there are no v under it
            if len(root_list[k]) == 0:
                del root_list[k]

        # add subscriptions ar our level
        total_sub += len(root_list.get(None, []))

        return total_sub





    def unsubscribe_all(self, owner, root_list=None):
        """
        Unsubscribe all function in our list that have a n owner that matches 'owner'
        """
        if root_list is None:
            root_list = self._listeners

        if None in root_list:   # don't bother checking if there's no listeners here
            root_list[None] = [x for x in root_list[None] if x[1] != owner]

        for k in root_list:
            if k is not None:  # special key for listener list
                for v in root_list[k]:
                        #call it again
                        self.unsubscribe_all(owner, root_list[k][v])


    def untrack_protocol(self, protocol):
        """
        Untracks the given protocol. You must call this when a protocol has closed to clean up after it.
        """
        self.unsubscribe_all(protocol)
        self.protocols.remove(protocol)


    def handle_broker_message(self, msg, message_callback):
        """
        Any message with topic type 'broker' should be passed into here.  'broker' messages are special messages
        that don't get 'published'. They are for querying the state of the system.
        'broker' messages have a 'request' field and will reply with an appropriate 'response' field

        message_callback is the function to call to send the message back to the protocol
        """
        if msg['TOPICS']['type'] != "broker":
            raise KeyError("handle_broker_message can only handle messages with 'TOPICS''type' == 'broker'")

        reply = {'TOPICS': {'type': 'broker', 'response': msg['TOPICS']['request']+"_response"},
                 'CONTENTS': {'status': "STATUS NOT FILLED IN" } }

        request = msg['TOPICS']['request']

        if request == 'get_protocols':
            reg = BaseProtocol.protocol_registry
            #make a dictionary of protocol names (keys) to (values) a dictionary of open params and defaults
            protocols = {k:{} for k in reg.keys()}
            for name in protocols.keys():
                protocols[name]["params"] = reg[name].get_open_params()
                protocols[name]["defaults"] = reg[name].get_open_params_defaults()

            reply['CONTENTS'] = protocols
            message_callback(reply)

        elif request == 'open_protocol':
            protocol_name = msg['CONTENTS']['protocol_name']
            open_params = msg['CONTENTS'].get('params', {})
            # make sure we know about the protocol
            if protocol_name not in BaseProtocol.protocol_registry:
                reply['TOPICS']['response'] = 'error'
                reply['CONTENTS'] = {'error': "No such protocol"}
                message_callback(reply) # send right away
            else:
                # we have the protocol! open it
                protocol_class = BaseProtocol.protocol_registry[protocol_name]
                d = defer.maybeDeferred(protocol_class.open, self, **open_params)

                def finished_open(p):
                    """We've finished opening the protocol"""
                    self.protocols.append(p)
                    reply['CONTENTS'] = {'name': str(p), 'STATUS': 'ok'}
                    message_callback(reply)

                d.addCallback(finished_open)

                def error_opening(e):
                    """ OOPS error while opening"""
                    reply['CONTENTS'] = {'STATUS': "Error while opening: " + str(e)}
                    message_callback(reply)

                d.addErrback(error_opening)

        elif request == 'get_open_protocols':
            # respond with the string repr of each protocol
            try:
                reply['CONTENTS']['protocols'] = [{"name": str(x), "protocol_type": getattr(x, "_protocol_type_name", "UNKNOWN")}
                                                  for x in self.protocols]
                reply['CONTENTS']['status'] = 'ok'
            except Exception as e:
                reply['CONTENTS']['status'] = 'Error while listing protocols: ' + str(e)

            message_callback(reply)

        elif request == 'close_protocol':
            #close the protocol with the string repr given
            open_protocols = [str(x) for x in self.protocols]
            reply['CONTENTS']['protocols'] = open_protocols

            to_close = msg['CONTENTS']['protocol']
            #see if its exits!
            if to_close not in open_protocols:
                reply['CONTENTS']['STATUS'] = "no such open protocol: " + to_close
                message_callback(reply)
                return

            new_protocol_list = []
            try:
                for x in self.protocols:
                    if str(x) == to_close:
                        x.close()
                    else:
                        new_protocol_list.append(x)

                self.protocols = new_protocol_list
                #recalc list
                reply['CONTENTS']['protocols'] = [str(x) for x in self.protocols]
                reply['CONTENTS']['STATUS'] = "ok"
                message_callback(reply)
            except NotImplementedError as e:
                reply['CONTENTS']['STATUS'] = "Error while closing protocol. Protocol does not define close() method"
                message_callback(reply)
            except Exception as e:
                reply['CONTENTS']['STATUS'] = "Error while closing protocol " + str(e)
                message_callback(reply)

        elif request == "get_discovery":
            cached_file_name = PARLAY_PATH + "/cached_discovery.json"
            # if we're forcing a refresh, or have no cache
            if msg['CONTENTS'].get('force', False) or not os.path.isfile(cached_file_name):
                d_list = []
                discovery = []
                for p in self.protocols:
                    d = defer.maybeDeferred(p.get_discovery)
                    #add this protocols discovery
                    def callback(x, protocol=p, error=None):
                        protocol_discovery = {'TEMPLATE': 'Protocol', 'NAME': str(protocol),
                                                              'protocol_type': getattr(protocol, "_protocol_type_name",
                                                                                       "UNKNOWN"),
                                                              'CHILDREN': x}
                        #extend with meta info
                        protocol_discovery.update(p.get_protocol_discovery_meta_info())
                        if error is not None:
                            protocol_discovery['error'] = x
                        discovery.append(protocol_discovery)

                    d.addCallback(callback)
                    d.addErrback(lambda e: callback([], error=e))

                    d_list.append(d)

                #wait for all to be finished
                all_d = defer.gatherResults(d_list, consumeErrors=True)
                def discovery_done(*args):

                    #append the discovery for the broker
                    discovery.append(Broker._discovery)
                    reply['CONTENTS']['status'] = 'ok'
                    reply['CONTENTS']['discovery'] = discovery
                    message_callback(reply)

                def discovery_error(*args):
                    #append the discovery for the broker
                    discovery.append(Broker._discovery)
                    
                    reply['CONTENTS']['status'] = str(args)
                    reply['CONTENTS']['discovery'] = discovery
                    message_callback(reply)

                all_d.addCallback(discovery_done)
                all_d.addErrback(discovery_error)
                with open(cached_file_name, 'w') as outfile:
                    json.dump(discovery, outfile)
            else:
                with open(cached_file_name) as json_data:
                    d = json.load(json_data)
                    reply['CONTENTS']['status'] = 'ok'
                    reply['CONTENTS']['discovery'] = d
                    message_callback(reply)





    def handle_subscribe_message(self, msg, message_callback):
        self.subscribe(message_callback, **(msg['CONTENTS']['TOPICS']))
        resp_msg = msg.copy()
        resp_msg['TOPICS']['type'] = 'subscribe_response'
        resp_msg['CONTENTS']['status'] = 'ok'

        #send the reply
        message_callback(resp_msg)

    def handle_unsubscribe_message(self, msg, message_callback):
        if hasattr(message_callback, 'im_self') and message_callback.im_self is not None:
            owner = message_callback.im_self
        else:
            raise ValueError("Function {} passed to handle_unsubscribe_message() ".format(message_callback.__name__) +
                             "must be a bound method of an object")

        self.unsubscribe(owner, msg['CONTENTS']['TOPICS'])
        resp_msg = msg.copy()
        resp_msg['TOPICS']['type'] = 'unsubscribe_response'
        resp_msg['CONTENTS']['status'] = 'ok'

        #send the reply
        message_callback(resp_msg)

    def run(self, mode=Modes.DEVELOPMENT, ssl_only=False):
        """
        Start up and run the broker. This method call with not return
        """
        from parlay.protocols.websocket import ParlayWebSocketProtocol
        if mode == Broker.Modes.DEVELOPMENT:
            print "WARNING: Broker running in DEVELOPER mode. Only use in a controlled development environment"
            print "WARNING: For production systems run the Broker in PRODUCTION mode. e.g.: " + \
                  "broker.run(mode=Broker.Modes.PRODUCTION)"

        #interface to listen on. In Development mode listen on everything
        #in production mode, only listen on localhost
        interface = '127.0.0.1' if mode == Broker.Modes.PRODUCTION else ""

        #ssl websocket
        contextFactory = ssl.DefaultOpenSSLContextFactory(PARLAY_PATH+'/keys/broker.key', PARLAY_PATH+'/keys/broker.crt')

        factory = WebSocketServerFactory("wss://localhost:" + str(self.secure_websocket_port))
        factory.protocol = ParlayWebSocketProtocol
        factory.setProtocolOptions(allowHixie76=True)
        listenWS(factory, contextFactory, interface=interface)

        webdir = static.File(PARLAY_PATH + "/ui/dist")
        webdir.contentTypes['.crt'] = 'application/x-x509-ca-cert'
        web = server.Site(webdir)
        self._reactor.listenSSL(self.https_port, web, contextFactory, interface=interface)

        if not ssl_only:
            #listen for websocket connections on port 8085
            factory = WebSocketServerFactory("ws://localhost:" + str(self.websocket_port))
            factory.protocol = ParlayWebSocketProtocol
            self._reactor.listenTCP(self.websocket_port, factory, interface=interface)

            #http server
            root = static.File(PARLAY_PATH + "/ui/dist")
            site = server.Site(root)
            self._reactor.listenTCP(self.http_port, site, interface=interface)

        self._reactor.run()

def main():
    d = Broker(reactor)
    print "\n Broker is running...\n"
    d.run()

if __name__ == "__main__":
    main()
