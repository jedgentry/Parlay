"""
Define a base class for creating a client script
"""

# a list of Endpoint proxy classes for Scripts
ENDPOINT_PROXIES = {}


from twisted.internet import threads, reactor, defer
from twisted.python.failure import Failure
from autobahn.twisted.websocket import  WebSocketClientProtocol, WebSocketClientFactory
import json
import sys
import traceback
from parlay.endpoints.parlay_standard import MSG_TYPES, MSG_STATUS
from parlay.protocols.utils import message_id_generator
import traceback

DEFAULT_TIMEOUT = 2
DEFAULT_ENGINE_WEBSOCKET_PORT = 8085

class ParlayScript(WebSocketClientProtocol):
    """Base object for all Parlay scripts"""

    # a list of functions that will be alerted when a new script instance is created
    stop_reactor_on_close = True

    def __init__(self):

        self.reactor = reactor
        self._msg_listeners = []
        self._system_errors = []
        self._system_events = []
        self._timer = None
        self.discovery = {}
        self.name = self.__class__.__name__ + ".py"

        self._message_id_generator = message_id_generator(sys.maxint, 100)

        # Add this listener so it will be first in the list to pickup errors, warnings and events.
        self.add_listener(self._system_listener)

    def open(self, protocol, **params):
        """

        :param protocol: protocol being used
        :param params: other parameters
        :return:
        """
        """
        :param protocol:
        :param params:
        :return:
        """
        msg = {'TOPICS': {'type': 'broker', 'request': 'open_protocol'}, "CONTENTS": {'protocol': protocol, 'params': params}}
        self.reactor.callFromThread(self.sendMessage, json.dumps(msg))

    def onConnect(self, response):
        WebSocketClientProtocol.onConnect(self, response)
        # schedule calling the script entry
        self.reactor.callLater(0, self._start_script)


    def add_listener(self, listener_function):
        """
        Add  functions to the listener list
        """
        self._msg_listeners.append(listener_function)

    ##################################################################################################################
    ###################  The functions below are used by the script ###############################
    def make_msg(self, to, command, msg_type=MSG_TYPES.COMMAND, direct=True, response_req=True, _extra_topics=None, **kwargs):
        """
        Prepare a message for the broker to disperse
        """
        msg = {'TOPICS': {}, 'CONTENTS': kwargs}
        if _extra_topics is not None:
            msg["TOPICS"] = _extra_topics

        # we can assume some keyword values
        msg['TOPICS']['TX_TYPE'] = 'DIRECT' if direct else "BROADCAST"
        msg['TOPICS']['MSG_TYPE'] = msg_type
        msg['TOPICS']['RESPONSE_REQ'] = response_req
        msg['TOPICS']['MSG_ID'] = self._message_id_generator.next()
        msg['TOPICS']['TO'] = to
        msg['TOPICS']['FROM'] = self.name
        msg['CONTENT']['COMMAND'] = command
        return msg

    def send_parlay_message(self, msg, timeout=DEFAULT_TIMEOUT):
        """
        Send a command.  This will be sent from the reactor thread.  If a response is required, we will wait
        for it.
        """
        wait = msg['TOPICS']['RESPONSE_REQ']
        if wait:
            #block the thread until we get a response or timeout
            resp = threads.blockingCallFromThread(self.reactor, self._sendParlayMessage, msg=msg, timeout=timeout)
            return resp
        else:
            #send this to the reactor without waiting for a response
            self.reactor.callFromThread(self.sendMessage, json.dumps(msg))

    def discover(self):
        print "Running discovery..."
        #block the thread until we get a discovery or error
        result = threads.blockingCallFromThread(self.reactor, self._in_reactor_discover)
        self.discovery = result
        return result


    def get_endpoint(self, endpoint_id):
        """
        Get an Endpoint Proxy object by the
        """

        # first see if we can find the endpoint by its ID
        endpoint_disc = self._find_endpoint_info_by_id(self.discovery, endpoint_id)
        if endpoint_disc is None:
            raise KeyError("Couldn't find endpoint with ID" + str(endpoint_id))

        # now that we have the discovery, let's try and construct a proxy out of it
        templates = [x.trim() for x in endpoint_disc.get("TEMPLATE", "").split("/")]
        template = None
        # find and stop at the first valid one
        for t in templates:
            if template is None:
                template = ENDPOINT_PROXIES.get(t, None)

        # if it's still None, then that means that we couldn't find it
        if template is None:
            raise KeyError("Couldn't find template proxy for:" + endpoint_disc.get("TEMPLATE", "") )

        # we have a good template class! Let's construct it
        return template(endpoint_disc)

    def _find_endpoint_info_by_id(self, discovery, endpoint_id):
        """
        Find the endpoint with a given id recursively (or None if it can't be found)
        @type: discovery list
        """
        for endpoint in discovery:
            if endpoint['ID'] == endpoint_id:
                return endpoint
            else:
                return self._find_endpoint_info_by_id(endpoint.get('CHILDREN', []), endpoint_id)

        # couldn't find it
        return None

    def sleep(self, timeout):
        threads.blockingCallFromThread(self.reactor, self._sleep, timeout)

    def _in_thread_run_script(self):
        """
        Run the script.
        """
        try:
            self.run_script()

        except Exception as e:
            # handle any exception thrown
            exc_type,exc_value,exc_traceback = sys.exc_info()
            print "Exception Error:  ",  exc_value

            # print traceback, excluding this file
            traceback.print_tb(exc_traceback)
            #exc_strings = traceback.format_list(traceback.extract_tb(exc_traceback))
            #exc_strings = [s for s in exc_strings if s.find("parlay_script.py")< 0 ]
            #for s in exc_strings:
            #    print s


    ####################### THe following  must be run from the reactor thread ####################################
    #############################   Do not call directly from script thread #####################
    def _sendParlayMessage(self, msg, timeout):
        """
        Send the command and wait for the callback.This must be called
        only from the reactor thread.
        NOTE: caller is blocked.
        @param msg: message to send
        """
        response = defer.Deferred()
        timer = None
        timeout_msg = {'TOPICS': {'MSG_TYPE': 'TIMEOUT'}}

        def listener(received_msg):
            # See if this is the response we are waiting for
            if received_msg['TOPICS']['MSG_TYPE'] == MSG_TYPES.RESPONSE:
                if received_msg['TOPICS']['TO'] == self.name and received_msg['MSG_ID'] == msg['TOPICS']['MSG_ID']:
                    if timer is not None:
                        #Clear the timer
                        timer.cancel()
                    if received_msg['MSG_STATUS'] == MSG_STATUS.ERROR:
                         #return error to waiting thread
                        response.errback(Failure(ErrorResponse(received_msg)))
                    else:
                        #send the response back to the waiting thread
                        response.callback(received_msg)
                    return True  # remove this listener from the list

            else:  # not our response.  Check for a system error.
                if len(self._system_errors) > 0:
                    if timer is not None:
                        # clear out the timer
                        timer.cancel()
                    # report an error to the waiting thread
                    response.errback(Failure(SystemError(self._system_errors.pop(0))))
                    return True  # remove this listener

            return False  # not for this listener - don't remove

        def cb(msg):
            # got a timeout or started with an error
            # remove the listener
            if listener in self.listener_list:
                self.listener_list.remove(listener)
            #send failure to thread waiting.
            response.errback(Failure(SystemError(msg)))

        # If we already have a system error, fail
        if len(self._system_errors) > 0:
            self._timer = self.reactor.callLater(0, cb, self._system_errors.pop(0))

        else:
            # set a timeout, if requested
            if timeout > 0:
                timer = self.reactor.callLater(timeout, cb, timeout_msg)

            # add our listener to the listener ist
            self.add_listener(listener)

            # send the message
            self.sendMessage(json.dumps(msg))

        return response

    def _in_reactor_discover(self):
        """
        Discovery called from within the reactor context
        """
        # call this back with the discovery
        result = defer.Deferred()
        #subscribe to response
        self.sendMessage(json.dumps({"TOPICS": {'type': 'subscribe'},
                                     "CONTENTS": {
                                         'TOPICS': {'response': 'get_discovery_response'}
                                     }
        }))
        #send request
        self.sendMessage(json.dumps({"TOPICS": {'type': 'broker', 'request': 'get_discovery'},
                                     "CONTENTS": {}
        }))

        def discovery_listener(msg):
            if msg['TOPICS'].get("type", "") != 'broker' and \
                            msg['TOPICS'].get("response", "") != "get_discovery_response":
                return False  # not the msg we're looking for

            if msg['CONTENTS'].get("status", "") == "ok":
                result.callback(msg['CONTENTS'].get('discovery', {}))
            else:
                result.errback(Failure(msg.get("status", "NO STATUS")))

            return True  # we're done here

        self.add_listener(discovery_listener)

        return result

    def _sleep(self, timeout):
        """
        Support a script delay.  The delay will stop early with an error if there is a system error.
        :param timeout:
        :return:deferred
        """
        response = defer.Deferred()
        timer = None
        def listener(received_msg):
            # look for system errors while we are waiting
            if len(self._system_errors) > 0:
                # cancel out the timer
                if timer is not None:
                    timer.cancel()
                #return the error to our waiting thread
                response.errback(Failure(SystemError(self.errors.pop(0))))
                return True  # remove the listener from the list
            return False  # don't remove

        def cb(msg):
            #remove our listener function if it is in the list.
            if listener in self._msg_listeners:
                self.listener_list.remove(listener)

            # if this is the normal timeout, just send the timeout message
            if msg['TOPICS']['MSG_TYPE'] == 'TIMEOUT':
                # Timed out - no error
                response.callback(msg)
            else:
                # Error
                response.errback(Failure(SystemError(msg)))

        # check we don't already have an error
        if len(self._system_errors)>0 :
             self._timer = self.reactor.callLater(0, cb, self._system_errors.pop(0))
        else:
            timer = self.reactor.callLater(timeout, cb, {'TOPICS': {'MSG_TYPE': 'TIMEOUT'}})
            self.add_listener(listener)
        return response


    def _start_script(self):
        """
        Init and run the script
        @param cleanup: Automatically clean up when we're done running
        """
        #run the script and run cleanup after.
        defer = threads.deferToThread(self._in_thread_run_script)
        defer.addBoth(self.cleanup)

    def run_script(self):
        """
        This should be overridden by the script class
        """
        raise NotImplementedError()


    def kill(self):
        """
        kill the current script
        """
        self.cleanup()

    def cleanup(self, *args):
        """
        Cleanup after running the script
        :param args:
        :return:
        """

        def internal_cleanup():

            self.transport.loseConnection()
            #should we stop the reactor on close?
            if self.__class__.stop_reactor_on_close:
                reactor.stop()

        self.sendClose()
        reactor.callLater(1, internal_cleanup)


    def _system_listener(self, msg):
        """
        This should be the first listener in the list. It will store any non-response errors and events
        :param msg:Msg from the broker
        :return: False so that it is never removed
        """

        # If it is not a response and it is an error, save it in the list
        if msg['TOPICS'].get('MSG_TYPE', "") != 'RESPONSE':
            status = msg['TOPICS'].get('MSG_STATUS', "")
            if status == 'ERROR':
                self._system_errors.append(msg)
            elif status == 'WARNING' or status == 'INFO':
                self._system_events.append(msg)
        return False

    def onMessage(self, packet, isBinary):
        """
        We got a message.  See who wants to process it.
        """
        if isBinary:
            print "Scripts don't understand binary messages"
            return

        msg = json.loads(packet)
        # run it through the listeners for processing
        self._runListeners(msg)

    def _runListeners(self, msg):
        remove_list = []
        for i, listener in enumerate(self._msg_listeners):
            if listener(msg):
                remove_list.append(i)

        # Now that we are done running the list, we can remove the ones slated for removal.
        if len(remove_list) > 0:
            self._msg_listeners = [x for i, x in enumerate(self._msg_listeners) if i not in remove_list]



def start_script(script_class, engine_ip='localhost', engine_port=DEFAULT_ENGINE_WEBSOCKET_PORT,
                 stop_reactor_on_close=None):
    """
    Construct a new script from the script class and start it
    """
    #set whether to stop the reactor or not (default to the opposite of reactor running)
    script_class.stop_reactor_on_close = stop_reactor_on_close if stop_reactor_on_close is not None else not reactor.running
    #connect it up
    factory = WebSocketClientFactory("ws://" + engine_ip + ":" + str(engine_port))
    factory.protocol = script_class
    reactor.connectTCP(engine_ip, engine_port, factory)

    if not reactor.running:
        reactor.run()



class ErrorResponse(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg
        self.description = error_msg['CONTENTS'].get('DESCRIPTION','')
        self.str = "Response Error: " + self.description

    def __str__(self):
        return self.str

class SystemError(Exception):
    """
    This error class if for  asynchronous system errors.
    """
    def __init__(self, error_msg):
        self.error_msg = error_msg
        self.description = error_msg['CONTENTS'].get('DESCRIPTION','')
        self.code = error_msg['CONTENTS'].get('ERROR_CODE',0)

    def __str__(self):
        return "Critical Error: " + self.description

