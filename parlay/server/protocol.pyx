

class Protocol(object):

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def get_devices(self):
        """
        Returns a deferred that will callback (or errback) with a list of discovered devices
        """
        raise NotImplementedError()