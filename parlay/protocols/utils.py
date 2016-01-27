"""
Generic utilities and helper functions that help make protocol development easier
"""
from collections import deque
from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import failure
from parlay.server.broker import Broker

class MessageQueue(object):
    """
    A basic message queue for messages that need to be acknowledged
    """

    def __init__(self, callback):
        """
        :param callback: A callback function that will be called every time we get a new message. This callback\
        should be of the form function(message) and must return a deferred that will be called back when it's
        done processing the message (or errback if there was an error)
        """
        self._q = deque()
        self._callback = callback
        #:type defer.Deferred
        self._active_sent = None  # deferred for the one we're sending

    def add(self, message):
        """
        Add a message to the queue
        self.waiting_for_ack_seq_num = None  # None = not waiting ... an int here, It will be sent in FIFO order

        :returns A deferred that will be called back (or err-backed) when the message is done processing
        :rtype defer.deferred
        """
        # is the queue empty?
        if len(self._q) == 0 and self._active_sent is None:

            self._active_sent = self._callback(message)
            self._active_sent.addBoth(self._done_with_msg)  # call this when we're finished
            return self._active_sent
        elif self._active_sent is not None:
            d = defer.Deferred()
            #queue up the message and the deferred to call
            self._q.append((message, d))
            return d
        else:
            raise RuntimeError("""Invalid message queue state! Queue not empty but not working on anything.
            Make sure that your callback function returns a deferred and calls it back properly""")



    def _done_with_msg(self, msg_result):
        if isinstance(msg_result, failure.Failure):
            print "Error encoding packet -- moving on to next packet"
            msg_result.printTraceback()

        #reactor.callLater(0, self._active_sent.callback, msg_result)
        # send the next one (if there is one)
        if len(self._q) > 0:
            next_msg, self._active_sent = self._q.popleft()
            # process the message, and set up our callback
            d = self._callback(next_msg)
            d.addBoth(self._done_with_msg)

        else:  # nothing left in queue
            self._active_sent = None






def message_id_generator(radix, min=0):
    """
    makes an infinite iterator that will be modulo radix
    """
    counter = min
    while True:
        yield counter
        counter = (counter + 1) % radix
        if counter < min:
            counter = min




def timeout(d, seconds):
    """
    Call d's errback if it hasn't been called back within 'seconds' number of seconds
    If 'seconds' is None, then do nothing
    """
    #get out of here if no timeout
    if seconds is None:
        return d

    timeout_deferred = defer.Deferred()
    d.addBoth(lambda x:  timeout_deferred.callback(x) if not timeout_deferred.called else None)

    def cancel():
        if not d.called:
            timeout_deferred.errback(failure.Failure(TimeoutError()))

    timer = reactor.callLater(seconds, cancel)
    return timeout_deferred


class TimeoutError(Exception):
    pass

def delay(timeout):
    d = defer.Deferred()
    Broker.get_instance()._reactor.callLater(timeout, lambda: d.callback(None))
    return d


class PrivateDeferred(defer.Deferred):
    """
    A Private Deferred is like a normal deferred, except that it can be passed around and callbacks can be attached
    by anone, but callback() and errback() have been overridden to throw an exception.  the private _callback() and _errback() must be used

    This ensures that only a user that 'knows what their doing' can issue the callback
    """

    def callback(self, result):
        raise AttributeError("Trying to call callback of Private Deferred. Only the deferred issuer may call callback")

    def errback(self, fail=None):
        raise AttributeError("Trying to call errback of Private Deferred. Only the deferred issuer may call errback")

    def _callback(self, result):
        return defer.Deferred.callback(self, result)

    def _errback(self, fail=None):
        return defer.Deferred.errback(self, fail)
