#setup leap imports
import os, sys, inspect
src_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
arch_dir = 'x64/' if sys.maxsize > 2**32 else 'x86/'
sys.path.insert(0, os.path.abspath(os.path.join(src_dir, arch_dir)))
print os.path.abspath(os.path.join(src_dir, arch_dir))
#standard leaps
import Leap
from parlay.protocols.protocol import BaseProtocol
from parlay.server.broker import Broker
from twisted.internet import defer
from twisted.internet.serialport import SerialPort
from twisted.protocols.basic import LineReceiver
from parlay.items.parlay_standard import ParlayCommandItem, parlay_datastream, parlay_command
from parlay.protocols.utils import delay
import math
import time

class LeapProtocol(BaseProtocol):
    """
    The Listener for the Leap controller
    """
    controller = None

    @classmethod
    def open(cls, broker):
        p = LeapProtocol()
        return p

    def __init__(self):
        #call parent __init__s
        BaseProtocol.__init__(self)

        if LeapProtocol.controller is None:
            LeapProtocol.controller = Leap.Controller()

        #add ourselves as a listener
        item = LeapItem()
        self.items = [item]
        #self.listener = LeapListener(item)
        #LeapProtocol.controller.add_listener(self.listener)


    def __str__(self):
        return "LEAP0_Protocol" # only 1 leap protocol at a time

class LeapListener(Leap.Listener):

    def __init__(self, item):
        self.item = item
        Leap.Listener.__init__(self)

    def on_connect(self, controller):
        print "LeapMotion Connected"
        # we have only one item


    def on_frame(self, controller):
        frame = controller.frame()

        leftmost = frame.hands.leftmost
        rightmost = frame.hands.rightmost
        hand1 = leftmost.palm_position.to_tuple() + (leftmost.direction.to_tuple(), leftmost.pinch_strength, leftmost.confidence)
        hand2 = rightmost.palm_position.to_tuple() + (rightmost.direction.to_tuple(), rightmost.pinch_strength, rightmost.confidence)
        self.item.hand1, self.item.hand2 = hand1, hand2
        self.item.hand_velocity = leftmost.palm_velocity


class LeapItem(ParlayCommandItem):

    stream1_x = parlay_datastream()
    stream1_y = parlay_datastream()
    stream1_z = parlay_datastream()

    def __init__(self):
        ParlayCommandItem.__init__(self, "LEAP0", "LEAP0")
        # x,y,z, (direction unit x,y,z, pinch_strength, confidence)openness position of hand1 (leftmost) and hand2 (rightmost)
        self.hand1 = (0, 0, 0, 0, 0, 0)  # parlay_datastream((0, 0, 0, 0, 0, 0))
        self.hand2 = (0, 0, 0, 0, 0, 0)  # parlay_datastream((0, 0, 0, 0, 0, 0))

        self.hand1_velocity = 0
        self.hand2_velocity = 0
        self.hand1_pitch = 0
        self.hand1_roll = 0
        self.hand1_grasp = 0

        self._sampling = False


    def _update_hand_info(self, frame):
        """
        Update the hand info with info from the frame
        """
        leftmost = frame.hands.leftmost
        rightmost = frame.hands.rightmost
        self.hand1 = leftmost.palm_position.to_tuple() + (leftmost.direction.to_tuple(), leftmost.pinch_strength, leftmost.confidence)
        self.hand2 = rightmost.palm_position.to_tuple() + (rightmost.direction.to_tuple(), rightmost.pinch_strength, rightmost.confidence)
        self.stream1_x, self.stream1_y, self.stream1_z = self.hand1[0:3]

        self.hand1_velocity = leftmost.palm_velocity
        self.hand2_velocity = rightmost.palm_velocity


        self.hand1_grasp = leftmost.pinch_strength
        self.hand1_pitch = leftmost.direction.pitch
        self.hand1_roll = leftmost.palm_normal.roll



    @parlay_command(async=True)
    def get_hands(self):
        return self.hand1, self.hand2

    @parlay_command()
    def link_up(self, arm_id):
        arm_id = "/dev/ttyUSB0"
        self.discover(force=False)
        arm = self.get_item_by_id(arm_id)
        print "connecting to: " + arm_id
        while True:
            # update hand position
            self._update_hand_info(LeapProtocol.controller.frame())
            x_leap = self.hand1[0]
            y_leap = self.hand1[1]
            z_leap = self.hand1[2]

            pitch_leap = self.hand1_pitch  # self.hand1[2]
            roll_leap = self.hand1_roll
            grasp_leap = self.hand1_grasp

            confidence_leap = self.hand1[-1]
            if confidence_leap > 0.3:

                x, y, z, pitch, grasp = self.leap_to_output_coords(x_leap, y_leap, z_leap, pitch_leap, grasp_leap)
                roll = math.degrees(self.hand1_roll)
                velocity = math.sqrt(self.hand1_velocity[0]**2 + self.hand1_velocity[1]**2 + self.hand1_velocity[2]**2)
                if velocity < 300: #15:
                    print "Robot Command (x, y, z, pitch, roll, grasp): {:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f} {:.1f}".format(x, y, z, pitch, roll, grasp, velocity)
                    #self.send_parlay_command(arm_name, "move_hand", x=x, y=y, z=z, wrist_pitch=pitch, wrist_roll=roll, grip=grasp)
                    arm.move_hand(x=x, y=y, z=z, wrist_pitch=pitch, wrist_roll=roll, grip=grasp)
                    #time.sleep(1)  # wait for a while so the move is deliberate
                else:  # faster iteration so we seem snappy
                    time.sleep(0.001)
            else:
                time.sleep(.001)


    @parlay_command(async=True)
    def start_sampling(self):
        #can only sample once
        if not self._sampling:
            self._sampling = True
            #we need to return, so have this guy work in the background until done
            @defer.inlineCallbacks
            def sample():
                while self._sampling:
                    self._update_hand_info(LeapProtocol.controller.frame())
                    yield delay(.1)  # sample every 10 ms

            sample()

    @parlay_command(async=True)
    def stop_sampling(self):
        self._sampling = False

    @staticmethod
    def leap_to_output_coords(x_leap, y_leap, z_leap, pitch_leap, grasp_leap):
        k_inch_mm = 1 / 25.4
        k_scale_x = 0.9
        k_scale_y = 1
        k_scale_z = 1

        pitch_scale = 1.00

        offset_x_out = 10.0
        offset_y_out = 0.0
        offset_z_out = -7
        offset_pitch_out = 8.0

        grasp = 2*(grasp_leap - 0.5) * 8 + 2
        pitch = math.degrees(pitch_leap)*pitch_scale + offset_pitch_out

        x = k_scale_x * k_inch_mm * -z_leap + offset_x_out
        y = k_scale_y * k_inch_mm * x_leap + offset_y_out
        z = k_scale_z * k_inch_mm * y_leap + offset_z_out

        return x, y, z, pitch, grasp
