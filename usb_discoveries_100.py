from parlay.utils import open_protocol, setup, discover, sleep
import parlay
from parlay.protocols.pcom.pcom_serial import PCOMSerial
from multiprocessing import Process
import time

NUM_DISCOVERIES = 0

if __name__ == '__main__':
    # p = Process(target=parlay.start, kwargs={"open_browser": True, "ui_path": "/Users/Matt/Downloads/build/"})
    p = Process(target=parlay.start, kwargs={"open_browser": True, "ui_path": "/Users/Matt/Promenade/OldParlayUI/"})
    p.start()
    time.sleep(8)
    print "DONE"
    setup()
    open_protocol("PCOMSerial", port="/dev/tty.usbmodem1451321")

    for i in range(NUM_DISCOVERIES):
        discover()
        sleep(2)
        print "Finished discovery #" + str(i)

    print "Successfully finished " + str(NUM_DISCOVERIES) + " discoveries."
