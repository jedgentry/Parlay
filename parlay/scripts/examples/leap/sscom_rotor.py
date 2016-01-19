from parlay.scripts.parlay_script import ParlayScript, start_script


class LeapSSCOMRotor(ParlayScript):

    def run_script(self):
        self.open("LeapProtocol")
        print "Discover"
        self.discover()

        leap = self.get_item_by_name("LEAP0")
        leap.start_sampling()

        #rotor = self.get_item(0xf001)
        #poll the stream
        while True:
            coords = (leap.stream1_x, leap.stream1_y, leap.stream1_z)
            print coords
            self.sleep(1)



start_script(LeapSSCOMRotor)