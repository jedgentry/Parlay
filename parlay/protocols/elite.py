"""
Protocols for Elite Engineering devices
"""
from parlay.protocols.protocol import BaseProtocol

from twisted.internet import defer
from twisted.internet.serialport import SerialPort

from parlay.endpoints.parlay_standard import ParlayCommandEndpoint, parlay_command
from serial_terminal import ASCIILineProtocol, LineEndpoint
from math import radians, degrees, sqrt, atan2, pi, acos, sin, cos, asin
from parlay.protocols.utils import delay


L0 = 8.5  # inches, upper arm length
L1 = 7.0  # inches, forearm length

THETA1_INIT = 0.0   # degrees

THETA2_INIT = 80.0  # degrees up from horizontal, corresponding to zero shoulder motor coordinate
THETA3_INIT = 35.0  # degrees down from straight, corresponding to zero elbow motor coordinate
THETA4_INIT = 25.0   # degrees up from straight, corresponding to zero wrist motor coordinate
THETA5_INIT = -90.0   # degrees from horizontal, corresponding to zero wrist rotation coordinate

BASE_ROT_ANGLE_TO_MOTOR = -90.0/3700.0 #-90.0/3750.0 # degrees per motor step count
SHOULDER_ANGLE_TO_MOTOR = -90.0/1200.0  # degrees per motor step count
ELBOW_ANGLE_TO_MOTOR = -45.0/1000.0

WRIST_PITCH_TO_MOTOR = -90.0/2200.0
WRIST_ROLL_TO_MOTOR = 90.0/1000.0

MAX_RADIUS = L0 + L1 - 1  # max radius to keep the arm within.
                          #  If instructed to go outside this radius, will instead touch the radius

class EliteArmProtocol(ASCIILineProtocol):

    @classmethod
    def open(cls, broker, port="/dev/tty.usbserial-FTAJOUB2"):
        if isinstance(port, list):
            port = port[0]

        EliteArmProtocol.delimiter = '\r'  # delimiter
        p = EliteArmProtocol(port)
        SerialPort(p, port, broker._reactor, baudrate=115200)

        return p

    @classmethod
    def get_open_params_defaults(cls):
        parent_args = ASCIILineProtocol.get_open_params_defaults()
        #just copy over the port list, we already know the baudrate and delimiter
        args = {}
        args["port"] = parent_args["port"]
        return args

    def __init__(self, port):
        BaseProtocol.__init__(self)
        self._parlay_name = port
        self.endpoints = [EliteArmEndpoint(self._parlay_name, "Elite Arm", self)]


class EliteArmEndpoint(LineEndpoint):
    """
    Endpoint for an Elite Arm
    """

    def __init__(self, endpoint_id, name, protocol):
        ParlayCommandEndpoint.__init__(self, endpoint_id, name)
        self._protocol = protocol
        self._inited = False
        self._in_move = False
        self._move_rate_ms = 5000


    @parlay_command(async=True)
    def home(self, motor_num):
        self.send_raw_data("HA"+str(motor_num))

    @defer.inlineCallbacks
    @parlay_command(async=True)
    def init_motors(self):
        self.send_raw_data("EAL")
        yield self.wait_for_ack()

        for i in range(5):
            self.send_raw_data("SRCD"+str(i+1))
            yield self.wait_for_ack()

    @defer.inlineCallbacks
    @parlay_command(async=True)
    def set_move_rate(self, rate_ms):
        for i in range(6):
            self.send_raw_data("SMT"+str(i+1)+" " + rate_ms)
            yield self.wait_for_ack()

        self._move_rate_ms = int(rate_ms)


    @defer.inlineCallbacks
    @parlay_command(async=True)
    def home_all(self):
        for x in range(6):
            self.home(x + 1)
            yield self.wait_for_ack(timeout_secs=15)

    @parlay_command(async=True)
    def shutdown(self):
        self.send_raw_data("SHUTDOWN")

    @defer.inlineCallbacks
    @parlay_command(async=True)
    def get_positions(self):
        self.send_raw_data("REFB")

        next_msg = yield self.wait_for_next_sent_msg()
        val_str = next_msg["CONTENTS"].get("DATA", "")
        # skip every other one (that's rate info)
        vals = [int(x) for x in val_str.split(" ") if int(x) % 2 == 0]
        defer.returnValue(vals)

    @defer.inlineCallbacks
    @parlay_command(async=True)
    def move_motor(self, motor, pos):
        self.send_raw_data("SPC"+str(int(motor)+1)+" "+str(int(pos)))
        yield self.wait_for_ack()

    @defer.inlineCallbacks
    @parlay_command(async=True)
    def move_all_motors(self, motor1, motor2, motor3, motor4, motor5, motor6):

        # apply limits on motors, rather than assert or return error
        motor1 = max(min(7500, int(motor1)), -7500)
        motor2 = max(min(1200, int(motor2)), -1200)
        motor3 = max(min(2700, int(motor3)), -2500)
        motor4 = max(min(800, int(motor4)), -2500)
        motor5 = max(min(4200, int(motor5)), -4200)

        if self._in_move:
            return  # we're already moving!! #TODO: Throw an exception
        try:
            self._in_move = True
            m = [motor1, motor2, motor3, motor4, motor5, motor6]
            for i in range(len(m)):
                self.send_raw_data("SPC"+str(i+1)+" "+str(int(m[i])))
                yield self.wait_for_ack()
        finally:
            self._in_move = False
            yield delay(self._move_rate_ms/1000 + .01)  # don't ACK until we're finished! (+1 ms for good measure)


    @defer.inlineCallbacks
    def move_all_motors_and_wait(self, motor1, motor2, motor3, motor4, motor5, motor6):
        self.move_all_motors(motor1, motor2, motor3, motor4, motor5, motor6)
        yield self.wait_for_ack()
        stationary = False
        old_pos = [None, None, None, None, None, None]
        while not stationary:
            yield delay(0.05)
            self.send_raw_data("REFB")
            next_resp = yield self.wait_for_next_sent_msg()
            pos = [int(x) for x in next_resp["CONTENTS"]["DATA"].split(" ")[::2] ]
            # are the all the same (e.g. haven't moved? since last reading?)
            stationary = all([pos[i] == old_pos[i] for i in range(6)])
            old_pos = pos

        print "Done Moving"


    @defer.inlineCallbacks
    @parlay_command(async=True)
    def move_hand(self, x, y, z, wrist_pitch, wrist_roll, grip): # grip is between -10 and 10
        """
        Kinematic move
        """
        try:
            print "Moving hands"
            x,y,z =float(x), float(y), float(z) # Kinematics.scale_to_max_radius(x,y,z)
            thetas = Kinematics.xyz_to_joint_angles(x, y, z)
            m1 = Kinematics.base_angle_to_motor(thetas[0])
            m2 = Kinematics.shoulder_angle_to_motor(thetas[1])
            m3 = Kinematics.elbow_angle_to_motor(thetas[2])
            m4 = Kinematics.wrist_pitch_to_motor(Kinematics.pitch_to_wrist_angle(thetas[1], thetas[2], float(wrist_pitch)))
            m5 = Kinematics.wrist_roll_to_motor(Kinematics.roll_to_wrist_roll_angle(float(wrist_roll)))

            m_g = float(grip)*3000
            print "t=", thetas
            print (m1, m2, m3, m4, m5, m_g)
            yield self.move_all_motors(m1, m2, m3, m4, m5, m_g)
        except Exception as e:
            print str(e)



#Math Functions
class Kinematics:

    @staticmethod
    def scale_to_max_radius(x, y, z):
        x, y, z = float(x), float(y), float(z)
        r = sqrt(x*x + y*y + z*z)
        if r > MAX_RADIUS:
            x = x*MAX_RADIUS/r
            y = y*MAX_RADIUS/r
            z = z*MAX_RADIUS/r

        return x, y, z

    @staticmethod
    def _xyz_to_cylindrical(x, y, z):
        """
        Converts cartesian coordinates x, y, z to cylindrical coordinates r, h, phi
        :param x: radially out at zero phi angle
        :param y: radially out at 90 deg phi angle
        :param z: strictly equal to height
        :return: height, radius, phi in degrees
        """
        r = sqrt(x**2 + y**2)
        h = z
        phi = degrees(atan2(y, x))

        return r, h, phi

    @staticmethod
    def _cylindrical_to_xyz(r, h, phi):
        x = r * cos(radians(phi))
        y = r * sin(radians(phi))
        z = h

        return x, y, z

    @staticmethod
    def xyz_to_joint_angles(x, y, z):
        """
        Inverse kinematics, convert desired hand position to required joint angles.

        Input coordinates are in inches.
        Output joint angles are in degrees.

        theta1 = Base rotation angle
        theta2 = Shoulder up angle
        theta3 = Elbow bend angle

        :param x: straight out along forward axis of arm.  Positive x moves away from base
        :param y: perpindicular to x, with no increase in height.  Positive y moves right from base perspective.
        :param z: height above base. Positive is up.
        :return: (theta1, theta2, theta3)
        """
        r, h, phi = Kinematics._xyz_to_cylindrical(x, y, z)

        d = sqrt(r**2 + h**2)

        theta3_rad = pi - acos((L0**2 + L1**2 - d**2) / (2 * L0 * L1))

        gamma_rad = acos((d**2 + L0**2 - L1**2) / (2 * L0 * d))
        beta_rad = asin(h / d)
        theta2_rad = gamma_rad + beta_rad

        theta1_rad = atan2(y, x)

        theta1 = degrees(theta1_rad) - THETA1_INIT
        theta2 = degrees(theta2_rad) - THETA2_INIT
        theta3 = degrees(theta3_rad) - THETA3_INIT

        return theta1, theta2, theta3

    @staticmethod
    def joint_angles_to_xyz(theta1, theta2, theta3):
        """
        Converts joint angles of arm into x, y, z cartesian coordinates
        :param theta1: arm base rotation angle in degrees
        :param theta2: arm shoulder up angle in degrees
        :param theta3: arm elbow bend angle in degrees
        :return: x, y, z in inches
        """
        theta2_rad = radians(theta2 + THETA2_INIT)
        theta3_rad = radians(theta3 + THETA3_INIT)

        r = L0 * cos(theta2_rad) + L1 * cos(theta2_rad - theta3_rad)
        h = L0 * sin(theta2_rad) + L1 * sin(theta2_rad - theta3_rad)
        phi = theta1 + THETA1_INIT

        x, y, z = Kinematics._cylindrical_to_xyz(r, h, phi)
        return x, y, z

    @staticmethod
    def pitch_to_wrist_angle(theta2, theta3, pitch):
        return pitch - theta2 + theta3 - THETA4_INIT

    @staticmethod
    def roll_to_wrist_roll_angle(roll):
        return roll - THETA5_INIT

    @staticmethod
    def shoulder_angle_to_motor(angle):
        return angle / SHOULDER_ANGLE_TO_MOTOR

    @staticmethod
    def elbow_angle_to_motor(angle):
        return angle / ELBOW_ANGLE_TO_MOTOR

    @staticmethod
    def base_angle_to_motor(angle):
        return angle / BASE_ROT_ANGLE_TO_MOTOR

    @staticmethod
    def wrist_pitch_to_motor(angle):
        return angle / WRIST_PITCH_TO_MOTOR

    @staticmethod
    def wrist_roll_to_motor(angle):
        return angle / WRIST_ROLL_TO_MOTOR





