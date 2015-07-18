import warnings
import threading
import numpy
import time
import random
import math
import sys
from ControlAlgorithm import OpenLoop, VelocityController

if sys.version_info < (3, 3):
    import gettime
    perf_counter = gettime.gettime
    print('> Controller: using gettime instead of perf_counter')
else:
    perf_counter = time.perf_counter

class Controller:

    def __init__(self, period = .01, echo = 0):

        # real-time loop
        self.period = period
        self.echo = echo
        self.echo_counter = 0
        self.is_running = False
        self.sleep = 0

        # data logger
        self.set_logger(60./period)

        # motor1
        self.motor1_on = False
        self.motor1_pwm = 0
        self.motor1_dir = 1

        # motor2
        self.motor2_on = False
        self.motor2_pwm = 0
        self.motor2_dir = 1

        # controller
        self.controller1 = OpenLoop()
        self.controller2 = None
        self.delta_mode = 0

        # references
        self.reference1_mode = 0 # 0 -> software, 1 -> potentiometer
        self.reference1 = 0
        self.reference2_mode = 0 # 0 -> software, 1 -> potentiometer
        self.reference2 = 0

    def set_motor1_pwm(self, value = 0):
        if value > 0:
            self.motor1_pwm = value
            self.motor1_dir = 1
        else:
            self.motor1_pwm = -value
            self.motor1_dir = -1

    def set_motor2_pwm(self, value = 0):
        if value > 0:
            self.motor2_pwm = value
            self.motor2_dir = 1
        else:
            self.motor2_pwm = -value
            self.motor2_dir = -1

    def set_delta_mode(self, value = 0):
        self.delta_mode = value

    def run(self):

        # Run the loop
        encoder1, pot1, encoder2, pot2 = self.read_sensors()
        time_stamp = perf_counter() - self.time_origin

        # Calculate delta T
        if self.delta_mode:
            time_delta = self.period
        else:
            time_delta = time_stamp - self.time_current
            # if abs(time_delta / self.period) > 1.2:
            #     print('time_delta = {}'.format(time_delta))

        # Update reference
        if self.reference1_mode:
            reference1 = 2 * (pot1 - 50)
        else:
            reference1 = self.reference1

        if self.reference2_mode:
            reference2 = 2 * (pot2 - 50)
        else:
            reference2 = self.reference2

        # Call controller
        pwm1 = pwm2 = 0
        if self.controller1 is not None:
            pwm1 = self.controller1.update(encoder1, reference1, time_delta)
            if pwm1 > 0:
                pwm1 = min(pwm1, 100)
            else:
                pwm1 = max(pwm1, -100)
            self.set_motor1_pwm(pwm1)

        if self.controller2 is not None:
            pwm2 = self.controller2.update(encoder2, reference2, time_delta)
            if pwm2 > 0:
                pwm2 = min(pwm2, 100)
            else:
                pwm2 = max(pwm2, -100)
            self.set_motor2_pwm(pwm2)

        # Log data
        self.data[self.current, :] = ( time_stamp,
                                       encoder1, reference1, pwm1,
                                       encoder2, reference2, pwm2 )

        if self.current < self.data.shape[0] - 1:
            # increment current pointer
            self.current += 1
        else:
            # reset current pointer
            self.current = 0
            self.page += 1

        # Echo
        if self.echo:
            coeff, self.echo_counter = divmod(self.echo_counter, self.echo)
            if self.echo_counter == 0:
                print('\r  {0:12.4f}'.format(time_stamp), end='')
                if self.controller1 is not None:
                    if isinstance(self.controller1, VelocityController):
                        print(' {0:+10.2f} {1:+6.1f} {2:+6.1f}'
                              .format(self.controller1.velocity,
                                      reference1, pwm1),
                              end='')
                    else:
                        print(' {0:+10.2f} {1:+6.1f} {2:+6.1f}'
                              .format(encoder1, reference1, pwm1),
                              end='')
                if self.controller2 is not None:
                    if isinstance(self.controller2, VelocityController):
                        print(' {0:+10.2f} {1:+6.1f} {2:+6.1f}'
                              .format(self.controller2.velocity,
                                      reference2, pwm2),
                              end='')
                    else:
                        print(' {0:+10.2f} {1:+6.1f} {2:+6.1f}'
                              .format(encoder2, reference2, pwm2),
                              end='')
            self.echo_counter += 1

        # Update current time
        self.time_current = time_stamp

    def _run(self):
        # Loop
        self.is_running = True
        self.time_current = perf_counter() - self.time_origin
        while self.is_running:
            # Call run
            self.run()
            # Sleep
            if self.sleep:
                time.sleep(self.sleep)

    def read_sensors(self):
        # Randomly generate sensor outputs
        return (random.randint(0,65355),
                random.randint(0,4095),
                random.randint(0,65355),
                random.randint(0,4095))

    # "public"

    def set_controller1(self, algorithm = None):
        self.controller1 = algorithm
        self.set_reference1(0)

    def set_controller2(self, algorithm = None):
        self.controller2 = algorithm
        self.set_reference2(0)

    def set_reference1(self, value = 0):
        self.reference1 = value

    def set_reference2(self, value = 0):
        self.reference2 = value

    def set_reference1_mode(self, value = 0):
        self.reference1_mode = value

    def set_reference2_mode(self, value = 0):
        self.reference2_mode = value

    def set_echo(self, value):
        self.echo = int(value)

    def set_sleep(self, duration):
        self.sleep = duration
        if self.period < duration:
            warnings.warn('Period has been increased to accomodate sleep')
            self.period = 1.1*duration

    def set_period(self, value = 0.1):
        self.period = value

    # TODO: Complete get methods
    # TODO: Test Controller

    def get_echo(self):
        return self.echo

    def get_sleep(self):
        return self.sleep

    def get_period(self):
        return self.period

    def set_logger(self, duration):
        self.data = numpy.zeros((math.ceil(duration/self.period), 7), float)
        self.reset_logger()

    def reset_logger(self):
        self.page = 0
        self.current = 0
        self.time_origin = perf_counter()
        self.time_current = 0 

    def get_log(self):
        if self.page == 0:
            return self.data[:self.current,:]
        else:
            return numpy.vstack((self.data[self.current:,:],
                                 self.data[:self.current,:]))

    def start(self):
        # Heading
        if self.echo:
            print('          TIME', end='')
            if self.controller1 is not None:
                if isinstance(self.controller1, VelocityController):
                    print('       VEL1   REF1   PWM1', end='')
                else:
                    print('       ENC1   REF1   PWM1', end='')
            if self.controller2 is not None:
                if isinstance(self.controller2, VelocityController):
                    print('       VEL1   REF1   PWM1', end='')
                else:
                    print('       ENC1   REF1   PWM1', end='')
            if self.controller2 is not None:
                if isinstance(self.controller2, VelocityController):
                    print('       VEL2   REF2   PWM2', end='')
                else:
                    print('       ENC2   REF2   PWM2', end='')
            print('')

        # Start thread
        self.thread = threading.Thread(target = self._run)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.echo:
            print('\n')


    def help(self):
        return ('S', """
----------------------------------------------------------------------
% General commands:
% > e - Echo message
% > H - Help
% > s - Status and configuration
% > S - Compact status and configuration
% > R - Read sensor, control and target

% Encoder commands:
% > Z - Zero encoder count

% Loop commands:
% > P int\t- set loop Period
% > E int\t- set Echo divisor
% > L [01]\t- run Loop (on/off)

% Motor commands:
% > G int\t- set motor Gain
% > V\t\t- reVerse motor direction
% > F [0123]\t- set PWM Frequency
% > Q [012]\t- set motor curve
% > M\t\t- start/stop Motors

% Target commands:
% > T int\t- set Target
% > B int\t- set target zero
% > O\t\t- read target pOtentiometer
% > D [01]\t- set target mode (int/pot)

% Controller commands:
% > K float\t- set proportional gain
% > I float\t- set Integral gain
% > N float\t- set derivative gain
% > Y [0123]\t- control mode (position/velocitY/open loop/off)
% > C\t\t- start/stop Controller
% > r - Read values
% > X - Finish / Break
----------------------------------------------------------------------
""")

    def get_status(self):
        return ('S', """
----------------------------------------------------------------------
% > s - Status and configuration
----------------------------------------------------------------------
""")

    def read_sensor(self):
        return ('S', """
----------------------------------------------------------------------
% > R - Read sensor, control and target
----------------------------------------------------------------------
""")


    def set_echo_divisor(self, value = 0):
        pass

    def run_loop(self, value = 0):
        pass

    def set_motor_gain(self, value = 0):
        pass

    def reverse_motor_direction(self, value = 0):
        return ('S', """
----------------------------------------------------------------------
% > V\t\t- reVerse motor direction
----------------------------------------------------------------------
""")

    def set_PWM_frequency(self, value = 0):
        pass

    def set_motor_curve(self, value = 0):
        pass

    def start_stop_motor(self, value = 0):
        return ('S', """
----------------------------------------------------------------------
% > M\t\t- start/stop Motor
----------------------------------------------------------------------
""")

    def set_target(self, value = 0):
        pass

    def set_target_zero(self, value = 0):
        pass

    def read_target_potentiometer(self, value = 0):
        return ('S', """
----------------------------------------------------------------------
% > O\t\t- read target pOtentiometer
----------------------------------------------------------------------
""")

    def set_target_mode(self, value = 0):
        pass

    def set_proportional_gain(self, value = 0):
        pass

    def set_integral_gain(self, value = 0):
        pass

    def set_derivative_gain(self, value = 0):
        pass

    def control_mode(self, value = 0):
        pass

    def start_stop_controller(self, value = 0):
        return ('S', """
----------------------------------------------------------------------
% > C\t\t- start/stop Controller
----------------------------------------------------------------------
""")

    def read_values(self):
        return ('S', """
----------------------------------------------------------------------
% > r - Read values
----------------------------------------------------------------------
""")



if __name__ == "__main__":

    from ControlAlgorithm import *

    controller = Controller()

    controller.set_sleep(0.1)
    controller.set_echo(1)
    controller.set_logger(2)

    controller.start()
    time.sleep(1)
    controller.set_reference1(100)
    time.sleep(1)
    controller.set_reference1(-50)
    time.sleep(1)
    controller.set_reference1(0)
    time.sleep(1)
    controller.stop()
