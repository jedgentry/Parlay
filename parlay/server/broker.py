"""

The broker is the main message router of the parlay system. The broker uses a standard publish/subscribe paradigm.
Modules that want to send message 'publish' the message to the broker and the broker sends a copy of that message to
 every connection that has 'subscribed' to messages with a matching topic signature. For more information on message types
 and structures.

 All messages must be key-value pairs (typically JSON strings or python dictionaries). The only requirement for messages
 is that every message must have, at its top level, a 'topics' key and a 'contents' key. 'topics' must be a key value pairing
 and can be subscribed to. 'contents' can be an object of any type and can **not** be subscribed to.

 Any message that isn't a 'special type' is implicitly a command to 'publish' that message.

 There are two 'special type' messages that are *not* published. The are distinguished by the 'type' topic.
 * 'type': 'broker' messages  are special commands to the broker. These messages and their foramt is defined on the protocol
  documentation page

 * 'type': 'subscribe' messages are a command to the broker to subscribe to a specific combination of topics. The 'contents'
 in a subscribe message must be simply the key 'topics' and a key-value pair of topics/values to subscribe to.
 e.g. :  (in JSON) {'topics':{'type':'subscribe'},'contents':{'topics':{'to':'Motor 1', 'id': 12345} } }
"""
from twisted.internet import reactor, defer
from parlay.protocols.protocol import BaseProtocol

from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from twisted.application import internet, service
from twisted.web import static, server
import os
import json

# path to the root parlay folder
PARLAY_PATH = os.path.dirname(os.path.realpath(__file__)) + "/.."

class Broker(object):
    """
    The Dispatcher is the sole holder of global state. There should be only one.
    It also coordinates all communication between protcols
    """
    instance = None

    def __init__(self, reactor):
        assert(Broker.instance is None)

        #the currently connected protocols
        self.protocols = []

        #The listeners that will be called whenever a message is received
        self._listeners = {}  # See Listener lookup document for more info

        self._reactor = reactor

        #THERE CAN BE ONLY ONE
        Broker.instance = self

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
        topic_type = msg['topics'].get('type', None)
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

        topics = msg['topics']
        #for each key in the listeners list
        for k in topics.keys():
            #if the key exists and  values match, then call any functions
            #or look further
                                  # root_list[k] is the value, which is a key to another dictionary
                                 #The None key in that dictionary will contain a list of funcs to call
                                # (Any other key will lead to yet another dictionary of keys and values)
            if k in root_list and topics[k] in root_list[k]:
                #recurse
                self._publish(msg, root_list[k][topics[k]])


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

    def unsubscribe(self, owner, topics):
        """
        unsubscribe owner from all subscriptions that match topics. Only EXACT matches will be unsubscribed
        """

        keys = sorted(topics.keys())
        root_list = self._listeners

        #go down the trie
        for k in keys:
            v = topics[k]

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
                for v in root_list[k]:
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





    def handle_broker_message(self, msg, message_callback):
        """
        Any message with topic type 'broker' should be passed into here.  'broker' messages are special messages
        that don't get 'published'. They are for querying the state of the system.
        'broker' messages have a 'request' field and will reply with an appropriate 'response' field

        message_callback is the function to call to send the message back to the protocol
        """
        if msg['topics']['type'] != "broker":
            raise KeyError("handle_broker_message can only handle messages with 'topics''type' == 'broker'")

        reply = {'topics': {'type': 'broker', 'response': msg['topics']['request']+"_response"},
                 'contents': {'status': "STATUS NOT FILLED IN" } }

        request = msg['topics']['request']

        if request == 'get_protocols':
            reg = BaseProtocol.protocol_registry
            #make a dictionary of protocol names (keys) to (values) a dictionary of open params and defaults
            protocols = {k:{} for k in reg.keys()}
            for name in protocols.keys():
                protocols[name]["params"] = reg[name].get_open_params()
                protocols[name]["defaults"] = reg[name].get_open_params_defaults()

            reply['contents'] = protocols
            message_callback(reply)

        elif request == 'open_protocol':
            protocol_name = msg['contents']['protocol_name']
            open_params = msg['contents'].get('params', {})
            # make sure we know about the protocol
            if protocol_name not in BaseProtocol.protocol_registry:
                reply['topics']['response'] = 'error'
                reply['contents'] = {'error': "No such protocol"}
                message_callback(reply) # send right away
            else:
                # we have the protocol! open it
                protocol_class = BaseProtocol.protocol_registry[protocol_name]
                d = defer.maybeDeferred(protocol_class.open, self, **open_params)

                def finished_open(p):
                    """We've finished opening the protocol"""
                    self.protocols.append(p)
                    reply['contents'] = {'name': str(p), 'status': 'ok'}
                    message_callback(reply)

                d.addCallback(finished_open)

                def error_opening(e):
                    """ OOPS error while opening"""
                    reply['contents'] = {'status': "Error while opening: " + str(e)}
                    message_callback(reply)

                d.addErrback(error_opening)

        elif request == 'get_open_protocols':
            # respond with the string repr of each protocol
            try:
                reply['contents']['protocols'] = [{"name": str(x), "protocol_type": getattr(x, "_protocol_type_name", "UNKNOWN")}
                                                  for x in self.protocols]
                reply['contents']['status'] = 'ok'
            except Exception as e:
                reply['contents']['status'] = 'Error while listing protocols: ' + str(e)

            message_callback(reply)

        elif request == 'close_protocol':
            #close the protocol with the string repr given
            open_protocols = [str(x) for x in self.protocols]
            reply['contents']['protocols'] = open_protocols

            to_close = msg['contents']['protocol']
            #see if its exits!
            if to_close not in open_protocols:
                reply['contents']['status'] = "no such open protocol: " + to_close
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
                reply['contents']['protocols'] = [str(x) for x in self.protocols]
                reply['contents']['status'] = "ok"
                message_callback(reply)
            except NotImplementedError as e:
                reply['contents']['status'] = "Error while closing protocol. Protocol does not define close() method"
                message_callback(reply)
            except Exception as e:
                reply['contents']['status'] = "Error while closing protocol " + str(e)
                message_callback(reply)

        elif request == "get_discovery":
            cached_file_name = PARLAY_PATH + "/cached_discovery.json"
            # if we're forcing a refresh, or have no cache
            if msg['contents'].get('force', False) or not os.path.isfile(cached_file_name):
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
                    reply['contents']['status'] = 'okay'
                    reply['contents']['discovery'] = discovery
                    message_callback(reply)

                def discovery_error(*args):
                    reply['contents']['status'] = str(args)
                    reply['contents']['discovery'] = discovery
                    message_callback(reply)

                all_d.addCallback(discovery_done)
                all_d.addErrback(discovery_error)
                with open(cached_file_name, 'w') as outfile:
                    json.dump(discovery, outfile)
            else:
                with open(cached_file_name) as json_data:
                    d = json.load(json_data)
                    reply['contents']['status'] = 'okay'
                    reply['contents']['discovery'] = d
                    message_callback(reply)





    def handle_subscribe_message(self, msg, message_callback):
        self.subscribe(message_callback, **(msg['contents']['topics']))
        resp_msg = msg.copy()
        resp_msg['topics']['type'] = 'subscribe_response'
        resp_msg['contents']['status'] = 'ok'

        #send the reply
        message_callback(resp_msg)

    def handle_unsubscribe_message(self, msg, message_callback):
        if hasattr(message_callback, 'im_self') and message_callback.im_self is not None:
            owner = message_callback.im_self
        else:
            raise ValueError("Function {} passed to handle_unsubscribe_message() ".format(message_callback.__name__) +
                             "must be a bound method of an object")

        self.unsubscribe(owner, msg['contents']['topics'])
        resp_msg = msg.copy()
        resp_msg['topics']['type'] = 'unsubscribe_response'
        resp_msg['contents']['status'] = 'ok'

        #send the reply
        message_callback(resp_msg)

    def run(self):
        """
        Start up and run the broker. This method call with not return
        """
        from parlay.protocols.websocket import BrokerWebsocketBaseProtocol

        #listen for websocket connections on port 8085
        factory = WebSocketServerFactory("ws://localhost:8085")
        factory.protocol = BrokerWebsocketBaseProtocol

        self._reactor.listenTCP(8085, factory)

        #http server
        root = static.File(PARLAY_PATH + "/ui/dist")
        site = server.Site(root)
        self._reactor.listenTCP(8080, site)
        self._reactor.run()

def main():
    d = Broker(reactor)
    print "\n Broker is running...\n"
    d.run()

if __name__ == "__main__":
    main()
