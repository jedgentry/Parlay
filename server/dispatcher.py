

class Dispatcher(object):
    """
    The Dispatcher is the sole holder of global state. There should be only one.
    It also coordinates all communication between protcols
    """
    instance = None

    def __init__(self):
        assert(Dispatcher.instance is None)

        #the currently connected protocols
        self.protocols = []

        #The listeners that will be called whenever a message is received
        self.listeners = {}  # See Listener lookup document for more info

        #THERE CAN BE ONLY ONE
        Dispatcher.instance = self

    def call_listeners(self, msg, root_list=None):
        """
        Call all of the listeners that match msg

        Time Complexity is O(2*n) * O(k)
        where:  n = the number of levels of the listener list
                k = the number of keys in the msg
        """
        if root_list is None: root_list = self.listeners
        #call any functions in the None key
        root_list[None] = [func for func in root_list.get(None, []) if not func(msg)]

        #for each key in the listeners list
        for k in msg.keys():
            #if the key exists and  values match, then call any functions
            #or look further
                                  # root_list[k] is the value, which is a key to another dictionary
                                 #The None key in that dictionary will contain a list of funcs to call
                                # (Any other key will lead to yet another dictionary of keys and values)
            if k in root_list and msg[k] in root_list[k]:
                #recurse
                self.call_listeners(msg, root_list[k])


    def register_listener(self, func, **kwargs):
        """
        Register a listener. The kwargs is a dictionary of args that **all** must be true
        to call this listener. You may register the same function multiple times with different
        kwargs, and it may be called multiple times for each message.
        """
        #sort so we always get the same order
        keys = sorted(kwargs.keys())
        root_list = self.listeners
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
        listeners.append(func)
        root_list[None] = listeners





