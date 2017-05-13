"""
Parlay Cloud util classes and functions
"""
import requests
import datetime
from threading import RLock
import json
from twisted.internet.task import LoopingCall
from parlay.server.broker import Broker, run_in_thread, run_in_broker
import os
from base64 import b64encode

# conditional imports for extra features
try:
    import cryptography
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.backends import default_backend
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
        time = time if time is not None else datetime.datetime.now()
        self["time"] = str(time)
        self["encoding"] = encoding


class DatapointManager(object):
    """
    A manager for storing and sending datapoints
    """

    REST_POST_URL = "http://localhost:8000/datapoint/api/v1/datapoint-create"
    HTTP_TIMEOUT = 5 # in seconds
    SYNC_EVERY = 60 * 5 # in seconds

    def __init__(self, uuid, channel, persistant_file, private_key_file, private_key_passphrase=None,
                 auto_sync_every=SYNC_EVERY,reactor=None):

        self._private_key_file = private_key_file
        self._private_key_passphrase = private_key_passphrase
        self._channel = channel
        self._persistance = persistant_file
        # authenticate with uuid and private key
        self._uuid = uuid
        self._lock = RLock()
        self._reactor = reactor if reactor is not None else Broker.get_instance().reactor
        self._auto_sync_call = None

        #see if the file exists, else create it
        if not os.path.isfile(persistant_file):
            self._set_persistance({"channel": str(channel), "uuid": str(uuid), "points": []})

        if auto_sync_every is not None and auto_sync_every > 0:
            self._auto_sync_call = LoopingCall(self.sync_to_cloud)
            self._auto_sync_call.start(auto_sync_every)

    @property
    def private_key(self):
        with open(self._private_key_file) as key_file:
            return serialization.load_pem_private_key(key_file.read(),
                                                             password=self._private_key_passphrase,
                                                             backend=default_backend())

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
        # get the id to set the datapoint to
        last_id = max([x["id"] for x in p["points"]]) if len(p["points"]) > 0 else -1
        last_id = max([last_id, p.get("last_id", -1)])

        datapoint["id"] = last_id + 1
        p["points"].append(datapoint)
        # set the persistant file
        self._set_persistance(p)
        # trigger a cloud update with retries

    @run_in_thread
    def sync_to_cloud(self):
        with self._lock:
            info = self._get_persistance()
            if len(info["points"]) == 0:  # if nothing to sync, then don't
                return

            # Serialize info into packet
            packet = {"points": json.dumps(info["points"]),
                      "channel": self._channel,
                      "uuid": self._uuid}
            # sign it
            signer = self.private_key.signer(padding.PKCS1v15(), hashes.SHA256())
            signer.update(bytes(packet["points"]))
            signature = signer.finalize()
            packet["sig"] = b64encode(signature)

            r = requests.post(DatapointManager.REST_POST_URL, json=packet, timeout=DatapointManager.HTTP_TIMEOUT)
            if r.status_code != 200:
                print r.status_code
                return

            response = r.json()
            print response
            last_id = response.get("last_id", 0)
            info['last_id'] = last_id
            # remove up to and including last_id
            info['points'] = [x for x in info["points"] if x["id"] > last_id]
            self._set_persistance(info)
            return last_id


# add a datapoint
if __name__ == "__main__":
    #DatapointManager.REST_POST_URL = "https://dev.parlay.cloud/datapoint/api/v1/datapoint-create"
    DatapointManager.REST_POST_URL = "http://localhost:5056/datapoint/api/v1/datapoint-create"
    manager = DatapointManager('b743156c-3772-11e7-bf44-80fa5b009d56', "test.python", "persist",
                               private_key_file="/tmp/test_parlay_device",
                               private_key_passphrase='PASSWORD',
                               auto_sync_every=None)
    point = Datapoint("31337", encoding="JSON")
    manager.add_datapoint(point)
    print manager.sync_to_cloud()


