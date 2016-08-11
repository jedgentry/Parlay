"""
Parlay Cloud util classes and functions
"""
import requests
import datetime
from threading import Lock
import json
import inspect
from parlay.server.broker import Broker

# conditional imports for extra features
try:
    from Crypto.Cipher import PKCS1_v1_5
    from Crypto.PublicKey import RSA
    SIGNATURE_ENABLED = True
# Can't use the pycrypto library to generate signatures. Have to use username/pass auth
except ImportError:
    print "parlay must be installed with 'secure' option to use cloud datapoints"
    print "install like :  pip install parlay[secure]"
    SIGNATURE_ENABLED = False

class Datapoint(dict):
    """
    A single Datapint
    """
    class Encoding:
        """
        Supported encoding
        """
        NULL= "NULL"

    def __init__(self, data, time=None, encoding=Encoding.NULL):
        super(Datapoint, self).__init__()
        self["data"] = data
        self["time"] = time if time is not None else datetime.datetime.now()
        self["encoding"] = encoding



class DatapointManager(object):
    """
    A manager for storing and sending datapoints
    """

    def __init__(self, uuid, channel, persistant_file, private_key_file, private_key_passphrase=None, reactor=None):

        self._private_key_file = private_key_file
        self._private_key_passphrase = private_key_passphrase
        self._channel = channel
        self._persistance = persistant_file
        # authenticate with uuid and private key
        self._uuid = uuid
        self._lock = Lock()
        self._reactor = reactor if reactor is not None else Broker.get_instance().reactor

    @@property
    def private_key(self):
        with open(self._private_key_file) as file:
           return RSA.importKey(file.read(), self._private_key_passphrase)

    def _get_persistance(self):
        """
        Get the persistance object as a dict
        :return:
        """
        with self._lock:
            with open(self._persistance,'r') as f:
                return json.load(f)


    def _set_persistance(self, obj):
        """
        Get the persistance object as a dict
        :return:
        """
        with self._lock:
            with open(self._persistance, 'w') as f:
                return json.dump(obj,f)

    def add_datapoint(self, datapoint):
        # get the persistant file
        p = self._get_persistance()
        # add the datapoint

        # set the persistant file
        # trigger a cloud update with retries





