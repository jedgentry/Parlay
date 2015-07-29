"""
Define a base class for creating a client script
"""

from twisted.internet import threads,reactor, defer
from twisted.internet.task import deferLater
from twisted.python.failure import Failure
from autobahn.twisted.websocket import  WebSocketClientProtocol, WebSocketClientFactory
import json
import sys
import collections




default_timeout = 10
message_id = 1
DEFAULT_ENGINE_WEBSOCKET_PORT = 8888

def get_message_id():
    global message_id
    #wrap at maxint
    if message_id >= sys.maxint:
        message_id = 0
    current = message_id
    message_id = current + 1
    return current

class ParlayScript(WebSocketClientProtocol):
    """Base object for all Avilon test scripts"""

    # a list of functions that will be alerted when a new script instance is created
    stop_reactor_on_close = True

    @classmethod
    def register_instance_listener(cls, listener):
        """
        Register a new instance listener that will be notified when there is a new instance
        """
        cls._instance_listeners.append(listener)

    def __init__(self):
        # messages received as passed through this list of listeners.
        self._listeners = []
        self.async_errors = []
        self.name = self.__class__.__name__ + ".py"
        self.reactor = reactor

    def onConnect(self, response):
        WebSocketClientProtocol.onConnect(self, response)
        # schedule a clean call
        self.reactor.callLater(0, self._start_script)


    def addListener(self, listener, timeout=None):
        """
        use this to add listener functions to the listener list
        """
        self._listeners.append(listener)  # ONLY APPEND NO PREPEND OR INSERT



    ##################################################################################################################
    ###################  The functions below are for this base class and are not usually used by the script ###########

    def makeCommand(self,to, command, response_req = True,**kwargs):
        """
        Put the necessary info into the message to get it to the engine
        """
        msg = {'TOPICS':{},'CONTENTS':kwargs}

        # we can assume some keyword values
        msg['TOPICS']['TX_TYPE']= 'DIRECT'
        msg['TOPICS']['MSG_TYPE']= 'COMMAND'
        msg['TOPICS']['RESPONSE_REQ']= response_req
        msg['TOPICS']['MSG_ID'] = get_message_id()
        msg['TOPICS']['TO'] = to
        msg['TOPICS']['FROM'] = self.name



        return msg


    def sendCommand(self,msg,wait=True, timeout=default_timeout,ignore_async_errors = False):
        """
        Send a command in the reactor thread and optionally wait for the
        response to return or timeout.
        """
        if wait:
            #block the thread until we get a response or timeout
            resp = threads.blockingCallFromThread(self.reactor,self.sendCommandWithDeferredWait,msg=msg, timeout=timeout,ignore_async_errors=ignore_async_errors)
            return resp
        else:
            #send this to the reactor without blocking
            #just send it from our thread
            self.reactor.callFromThread(self.sendMessage,json.dumps(msg))

    def delay(self,time,ignore_async_errors=False):
        threads.blockingCallFromThread(self.reactor,self.deferredDelay,time,ignore_async_errors=ignore_async_errors)

    ####  Calls only made from the reactor thread ##
    #### Do not call directly    ######
    def deferredDelay(self,time,ignore_async_errors):
        """
        This is what is run on the reactor side for a delay.  It will pickup message looking for errors, and
        break out of the delay upon error.
        :param time:
        :return:
        """
        response = defer.Deferred()
        timer = None
        def listener(new_msg):
            # look for async errors and resume blocked thread if found
            if len(self.async_errors) > 0:
                # we got an error while waiting our delay.
                # cancel out the timer
                if timer is not None:
                    timer.cancel()
                #return the error to our waiting thread
                error_msg = self.async_errors.pop()
                response.errback(Failure(AsyncError(error_msg)))
                return True # remove the listener
            return False  # not for this listener - don't remove

        def cb(msg):
            #remove our listener
            if listener in self._listeners:
                self._listeners.remove(listener)
            # see if this an error message or wait completed messsage

            if msg['TOPIC']['MSG_TYPE'] == 'TIMEOUT':
                # times up - no errors
                response.callback(msg)
            else:
                # got an asynchronous error
                response.errback(Failure(AsyncError(msg)))

        # if we already got an async error before starting the delay, setup a failure.
        if not ignore_async_errors and len(self.async_errors)>0:
            error_msg= self.async_errors.pop()
            timer = self.reactor.callLater(0,cb,error_msg)

        else: # set up our delay
            timer = self.reactor.callLater(time,cb,{'TOPIC':{'MSG_TYPE':'TIMEOUT'}})
            #add the listener for an async error response while we are waiting
            if not ignore_async_errors:
                self.addListener(listener)
        return response

    def sendCommandWithDeferredWait(self, msg,timeout,ignore_async_errors):
        """
        Send the command and wait for the callback.This must be called
        only from the reactor thread.
        NOTE: caller is blocked.
        @param msg: message to send
        """
        response = defer.Deferred()
        timer = None
        timeout_msg = {'TOPIC':{'MSG_TYPE':'TIMEOUT'}}

        def listener(new_msg):
            # if this is direct to us, give result back to blocked caller
            if new_msg['TOPIC']['MSG_TYPE']== 'RESPONSE':
                if new_msg['TOPIC']['TO'] == self.name and new_msg['MSG_ID']==msg['TOPIC']['MSG_ID']:
                    if timer is not None:
                        #haven't timed out yet. Clear the timer
                        timer.cancel()
                    if new_msg['MSG_STATUS']== 'ERROR':
                         #return error to blocked thread
                        response.errback(Failure(ErrorResponse(new_msg)))
                    else:
                        #all good
                        response.callback(new_msg)
                    return True  # remove this
            else: #not to us - but may be an asynchronous error
                if len(self.async_errors)> 0 and not ignore_async_errors:
                    if timer is not None:
                        # clear out the timer
                        timer.cancel()
                         # report an error to the waiting thread
                    error_msg = self.async_errors.pop()
                    response.errback(Failure(AsyncError(error_msg)))
                    return True # remove this listener

            return False  # not for this listener - don't remove

        def cb(msg):
            # got a timeout or started with an error
            # remove the listener
            if listener in self._listeners:
                self._listeners.remove(listener)
            #send failure to thread waiting.
            response.errback(Failure(AsyncError(msg)))

        # if we got an async error before this call, setup a failure.
        if len(self.async_errors)>0 and not ignore_async_errors:
             error_msg = self.async_errors.pop()
             timer = self.reactor.callLater(0,cb,error_msg)

        # set a timer, if one was requested
        else:
            #set a timer if requested
            if timeout > 0:
                timer = self.reactor.callLater(timeout,cb,timeout_msg)

            #setup a listener for the response
            self.addListener(listener)

            # send the message
            self.sendMessage(json.dumps(msg))
        return response

    def _error_listener(self, msg):
        """
        listener called from the reactor thread  - always look for errors and store them
        other listeners will see the stored error.  Note this is the first listener in the list, therefore
        it will always be run before other listeners.
        :param msg:
        :return:
        """
        """
        :param msg:
        :return:
        """
        # look for asynchronous errors.  Note: these will not have a message ID field.
        if 'MSG_ID' not in msg['TOPICS']:
            if 'MSG_STATUS'in msg and msg['MSG_STATUS'] == 'ERROR':
                 # save the error
                self.async_errors.append(msg)
        return False

    def _start_script(self):
        """
        Init and run the script
        @param cleanup: Automatically clean up when we're done running
        """
        #run the script and store its deferred

        d = threads.deferToThread(self.run_script_thread)
        #when we're finished call the finished deferred's callback so everyone can be alerted!
        d.addBoth(self.cleanup)

    def run_script_thread(self):
        """
        This runs the script and is in the script thread.
        """

        try:
            self.run_script()

        except:
            self.printException()
            raw_input("Exception: Press 'Enter' to continue.")

    def onMessage(self, packet):
        """
        We got a message. Process any listeners that are waiting for messages
        """
        msg = json.loads(packet)
        #see if we have a listener for this message
        self._run_listeners(msg)

    def _run_listeners(self, msg):
        to_remove = []
        for i, listener in enumerate(self._listeners):
             if listener(msg):
                to_remove.append(i)

        #now remove all listeners in the list
        if len(to_remove) > 0:
            self._listeners = [x for i, x in enumerate(self._listeners) if i not in to_remove]


    # def _waitForDependencies(self, *args):
    #     """
    #     Returns a deferred that will be called once all dependencies are done
    #     """
    #     return defer.gatherResults(self._depends_on)

    def kill(self):
        """
        kill the current script as soon as possible
        """
        #self._run_script_coroutine.cancel()
        #for x in self._depends_on:
        #    x.cancel()

        #clean up ASAP
        self.cleanup()



    def cleanup(self, *args):
        """cleanup after we're finished"""

        def internal_cleanup():

            self.transport.loseConnection()
            #should we stop the reactor on close?
            if self.__class__.stop_reactor_on_close:
                reactor.stop()

        self.sendClose()
        reactor.callLater(1, internal_cleanup)


    def run_script(self):
        """
        Runs the actual script. Override this in your sub-script class
        """

        raise NotImplementedError()




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
        self.response = error_msg
        self.str = str(error_msg)
        if 'description' in error_msg:
            self.str = "Response Message: " + error_msg['description'] + '\n'+ self.str

    def __str__(self):
        return self.str



class AsyncError(Exception):
    def __init__(self, error_msg):
        self.response = error_msg
        self.str = str(error_msg)
        if 'DESCRIPTION' in error_msg['CONTENTS']:
            self.str =  "Error: " + error_msg['CONTENTS']['DESCRIPTION'] + '\n' + self.str

    def __str__(self):
        return self.str
