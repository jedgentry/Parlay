from serial.tools import list_ports


def print_usb_info():
    """
    Global function used to print information about currently connected USBs
    :return:
    """

    print "\nParlay USB Identification Tool\n"
    print "==========================================="
    for port in list_ports.comports():
        print "USB DESCRIPTOR: {0}".format(port.description)
        print "VENDOR ID: {0}".format(port.vid)
        print "PRODUCT ID: {0}".format(port.pid)
        print "PATH: {0}".format(port.device)
        print "==========================================="

if __name__ == "__main__":
    print_usb_info()