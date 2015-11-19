# a list of Endpoint proxy classes for Scripts
ENDPOINT_PROXIES = {}

from twisted.internet import threads, reactor, defer
from parlay.endpoints.base import MSG_TYPES, MSG_STATUS
from parlay.protocols.utils import message_id_generator
from twisted.python.failure import Failure
from base import BaseEndpoint
import sys

DEFAULT_TIMEOUT = 120

class ThreadedEndpoint(BaseEndpoint):
    """Base object for all Parlay scripts"""

    # a list of functions that will be alerted when a new script instance is created
    stop_reactor_on_close = True

    def __init__(self, endpoint_id, name):
        BaseEndpoint.__init__(self, endpoint_id, name)
        self.reactor = self._broker._reactor
        self._msg_listeners = []
        self._system_errors = []
        self._system_events = []
        self._timer = None
        self.discovery = {}

        self._message_id_generator = message_id_generator(sys.maxint, 100)

        # Add this listener so it will be first in the list to pickup errors, warnings and events.
        self.add_listener(self._system_listener)



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



    def open(self, protocol, **params):
        """
        :param protocol: protocol being used
        :param params: other parameters
        :return:
        """
        msg = {'TOPICS': {'type': 'broker', 'request': 'open_protocol'}, "CONTENTS": {'protocol_name': protocol, 'params': params}}
        self.reactor.callFromThread(self._send_parlay_message, msg)

        def wait_for_response():
            result = defer.Deferred()
            def listener(msg):
                if msg['TOPICS'].get('response', "") == 'open_protocol_response':
                    if msg['CONTENTS']['STATUS'] == 'ok':
                        result.callback(msg['CONTENTS']['STATUS'])
                    else:
                        result.errback(Failure(msg['CONTENTS']['STATUS']))
                    return True  # we're done here
                return False  # keep waiting
            self.add_listener(listener)
            return result

        threads.blockingCallFromThread(self.reactor, wait_for_response)

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
        msg['TOPICS']['FROM'] = self.endpoint_id
        msg['CONTENTS']['COMMAND'] = command
        return msg

    def send_parlay_message(self, msg, timeout=DEFAULT_TIMEOUT, wait=None):
        """
        Send a command.  This will be sent from the reactor thread.  If a response is required, we will wait
        for it.
        :param msg The Message to send
        :param timeout If we require a response and don't get one back int timeout seconds, raise a timeout exception
        :param wait If set to True, will block until a response, if false will continue without blocking,
        If set to None, till auto discover based on message RESPONSE_REQ.
        """
        if wait is None:
            wait = msg['TOPICS'].get('RESPONSE_REQ', False)

        if wait:
            #block the thread until we get a response or timeout
            return threads.blockingCallFromThread(self.reactor, self._send_parlay_message_from_thread, msg=msg, timeout=timeout)
        else:
            #send this to the reactor without waiting for a response
            self.reactor.callFromThread(self._send_parlay_message, msg)
            return None  # nothing to wait on, no response


    def discover(self, force=True):
        """
        Run a discovery so that the script knows what endpoints are attached and can get handles to them.
        :param force If True, will force a rediscovery, if False will take the last cached discovery
        """
        print "Running discovery..."
        #block the thread until we get a discovery or error
        result = threads.blockingCallFromThread(self.reactor, self._in_reactor_discover, force)
        self.discovery = result
        return result

    def get_endpoint_by_id(self, endpoint_id):
        endpoint_disc = self._find_endpoint_info(self.discovery, endpoint_id, "ID")
        if endpoint_disc is None:
            raise KeyError("Couldn't find endpoint with id " + str(endpoint_id))
        else:
            return self._proxy_endpoint(endpoint_disc)

    def get_endpoint_by_name(self, endpoint_name):
        endpoint_disc = self._find_endpoint_info(self.discovery, endpoint_name, "NAME")
        if endpoint_disc is None:
            raise KeyError("Couldn't find endpoint with name " + str(endpoint_name))
        else:
            return self._proxy_endpoint(endpoint_disc)

    def _proxy_endpoint(self, endpoint_disc):
        """
        Get an Endpoint Proxy object by the discovery
        :param endpoint_disc The endpoint discovery object
        :type endpoint_disc dict
        """
        # Do we have a valid endpoint discovery object?
        if endpoint_disc is None:
            raise KeyError("Couldn't make Proxy Endpoint with None type")

        # now that we have the discovery, let's try and construct a proxy out of it
        templates = [x.strip() for x in endpoint_disc.get("TYPE", "").split("/")]
        template = None
        # find and stop at the first valid one
        for t in templates:
            if template is None:
                template = ENDPOINT_PROXIES.get(t, None)

        # if it's still None, then that means that we couldn't find it
        if template is None:
            raise KeyError("Couldn't find template proxy for:" + endpoint_disc.get("TYPE", ""))

        # we have a good template class! Let's construct it
        return template(endpoint_disc, self)

    def _find_endpoint_info(self, discovery, endpoint_id, key):
        """
        Find the endpoint with a given id recursively (or None if it can't be found)
        @type: discovery list
        """
        for endpoint in discovery:
            if endpoint.get(key, None) == endpoint_id:
                return endpoint
            found = self._find_endpoint_info(endpoint.get('CHILDREN', []), endpoint_id, key)
            # did a child find it?
            if found is not None:
                return found
        return None


    def sleep(self, timeout):
        threads.blockingCallFromThread(self.reactor, self._sleep, timeout)




    ####################### THe following  must be run from the reactor thread ####################################
    #############################   Do not call directly from script thread #####################
    def _send_parlay_message_from_thread(self, msg, timeout):
        """
        Send the command and wait for the callback.This must be called
        only from the reactor thread.
        NOTE: caller is blocked.
        :param msg: message to send
        :param timeout timeout ins econds
        """
        response = defer.Deferred()
        timer = None
        timeout_msg = {'TOPICS': {'MSG_TYPE': 'TIMEOUT'}}

        def listener(received_msg):
            # See if this is the response we are waiting for
            if received_msg['TOPICS'].get('MSG_TYPE', "") == MSG_TYPES.RESPONSE:
                if received_msg['TOPICS']['TO'] == self.endpoint_id and\
                                received_msg['TOPICS'].get('MSG_ID', None) == msg['TOPICS']['MSG_ID']:
                    if received_msg['TOPICS'].get('MSG_STATUS', "") == MSG_STATUS.ACK:
                        return False  # keep waiting, an ACK means its not finished yet, it jsut got our msg
                    if timer is not None:
                        #Clear the timer
                        timer.cancel()
                    if received_msg['TOPICS'].get('MSG_STATUS', "") == MSG_STATUS.ERROR:
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
            if listener in self._msg_listeners:
                self._msg_listeners.remove(listener)
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
            self._send_parlay_message(msg)

        return response

    def _send_parlay_message(self, msg):
        """
        Send a dictionary msg.  Must be filled in by subclass with protocol specific implementation
        """

        raise NotImplementedError()

    def _in_reactor_discover(self, force):
        """
        Discovery called from within the reactor context
        """
        # call this back with the discovery
        result = defer.Deferred()

        def discovery_listener(msg):
            if msg['TOPICS'].get("type", "") != 'broker' and \
                            msg['TOPICS'].get("response", "") != "get_discovery_response":
                return False  # not the msg we're looking for

            if msg['CONTENTS'].get("status", "") == "ok":
                result.callback(msg['CONTENTS'].get('discovery', {}))
            else:
                result.errback(Failure(Exception(msg.get("status", "NO STATUS"))))

            return True  # we're done here

        self.add_listener(discovery_listener)

        self._send_parlay_message({"TOPICS": {'type': 'broker', 'request': 'get_discovery'},
                                     "CONTENTS": {'force': force}
        })

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
                self._msg_listeners.remove(listener)

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


    def _runListeners(self, msg):
        remove_list = []
        for i, listener in enumerate(self._msg_listeners):
            if listener(msg):
                remove_list.append(i)

        # Now that we are done running the list, we can remove the ones slated for removal.
        if len(remove_list) > 0:
            self._msg_listeners = [x for i, x in enumerate(self._msg_listeners) if i not in remove_list]

class ErrorResponse(Exception):
    def __init__(self, error_msg):
        self.error_msg = error_msg
        self.description = error_msg['CONTENTS'].get('DESCRIPTION', '')
        self.str = "Response Error: " + self.description

    def __str__(self):
        return self.str

class SystemError(Exception):
    """
    This error class if for  asynchronous system errors.
    """
    def __init__(self, error_msg):
        self.error_msg = error_msg
        self.description = error_msg.get('CONTENTS', {}).get('DESCRIPTION', '')
        self.code = error_msg.get('CONTENTS', {}).get('ERROR_CODE', 0)

    def __str__(self):
        return "Critical Error: " + self.description + "CODE: " + self.code + " MSG:" + self.error_msg