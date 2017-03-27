import warnings
import time

from time import perf_counter

from ctrl import block
from ctrl.block import clock

import rcpy
import rcpy.mpu9250 as mpu

# Uses Alex Martelli's Borg for making MPU9250 a singleton

class MPU9250(clock.Clock):

    _shared_state = {}

    def __init__(self, **kwargs):

        # Makes sure clock is a singleton
        self.__dict__ = self._shared_state

        # Do not initialize if already initialized
        if not self.__dict__ == {}:
            warnings.warn('> Clock is already initialized. Skipping call to __init')
            return

        # get defaults
        defaults = mpu.mpu9250.get()
        
        # accel_fsr
        self.accel_fsr = kwargs.pop('accel_fsr', defaults.accel_fsr)

        # gyro_fsr
        self.gyro_fsr = kwargs.pop('gyro_fsr', defaults.gyro_fsr)

        # accel_dlpf
        self.accel_dlpf = kwargs.pop('accel_dlpf', defaults.accel_dlpf)

        # gyro_dlpf
        self.gyro_dlpf = kwargs.pop('gyro_dlpf', defaults.gyro.dlpf)

        # enable_magnetometer 
        self.enable_magnetometer = kwargs.pop('enable_magnetometer',
                                              defaults.enable_magnetometer)

        # orientation
        self.orientation = kwargs.pop('orientation', defaults.orientation)

        # compass_time_constant
        self.compass_time_constant = kwargs.pop('compass_time_constant',
                                                defaults.compass_time_constant)

        # dmp_interrupt_priority
        self.dmp_interrupt_priority = kwargs.pop('dmp_interrupt_priority',
                                                 defaults.dmp_interrupt_priority)

        # dmp_sample_rate
        self.period = kwargs.pop('period',
                                 1/defaults.dmp_sample_rate

        # show_warnings
        self.show_warnings = kwargs.pop('show_warnings',
                                        defaults.show_warnings)

        # enable_dmp 
        self.enable_dmp = kwargs.pop('enable_dmp',
                                     defaults.enable_dmp)
        
        # enable_fusion 
        self.enable_fusion = kwargs.pop('enable_fusion',
                                        defaults.enable_fusion)

        # call super
        super().__init__(**kwargs)

        # initialize mpu9250
        mpu.mpu9250.initialize(accel_fsr = self.accel_fsr,
			       gyro_fsr = self.gyro_fsr,
			       accel_dlpf = self.accel_dlpf,
			       gyro_dlpf = self.gyro_dlpf,
			       enable_magnetometer = self.enable_magnetometer,
			       orientation = self.orientation,
			       compass_time_constant = self.compass_time_constant,
			       dmp_interrupt_priority = self.dmp_interrupt_priority,
			       dmp_sample_rate = 1/self.dmp_sample_rate,
			       show_warnings = self.show_warnings,
			       enable_dmp = self.enable_dmp,
			       enable_fusion = self.enable_fusion)
                                 
        self.data = {}
                                          
    def get(self, *keys, exclude = ()):

        # call super excluding time and last
        return super().get(*keys, exclude = exclude + ('data',
                                                       '_shared_state'))
                                          
    def set(self, exclude = (), **kwargs):

        # call super
        super().set(exclude + ('data',
                               '_shared_state'), **kwargs)

        # initialize mpu9250
        mpu.mpu9250.initialize(accel_fsr = self.accel_fsr,
			       gyro_fsr = self.gyro_fsr,
			       accel_dlpf = self.accel_dlpf,
			       gyro_dlpf = self.gyro_dlpf,
			       enable_magnetometer = self.enable_magnetometer,
			       orientation = self.orientation,
			       compass_time_constant = self.compass_time_constant,
			       dmp_interrupt_priority = self.dmp_interrupt_priority,
			       dmp_sample_rate = 1/self.dmp_sample_rate,
			       show_warnings = self.show_warnings,
			       enable_dmp = self.enable_dmp,
			       enable_fusion = self.enable_fusion)
    
    def get_data(self):

        return self.data

    def read(self):

        #print('> read')
        if self.enabled:

            # Read imu and store data (blocking call)
            self.data = mpu.mpu9250.read()

        # call super
        return super().read()


class Raw(block.BufferBlock):
        
    def __init__(self, **kwargs):

        # call super
        super().__init__(**kwargs)

        # set MPU9250 block
        self.mpu9250 = MPU9250() # singleton

    def get(self, *keys, exclude = ()):

        # call super excluding time and last
        return super().get(*keys, exclude = exclude + ('mpu9250'))
                                          
    def set(self, exclude = (), **kwargs):

        # call super
        super().set(exclude + ('mpu9250'), **kwargs)

    def read(self):

        #print('> read')
        if self.enabled:

            # read imu
            data = self.mpu9250.get_data()

            # units (m/s^2) and (rad/s)
            self.buffer = (data['accel'], data['gyro'])
        
        # call super
        return super().read()

class Inclinometer(Raw):

    def __init__(self, **kwargs):

        # turns initialization
        self.turns = kwargs.pop('turns', 0)
        self.theta = kwargs.pop('theta', 0)
        self.threshold = kwargs.pop('threshold', 0.25)

        # call super
        super().__init__(**kwargs)

    def reset(self):

        self.turns = 0
        
    def read(self):

        #print('> read')
        if self.enabled:

            # read imu
            data = self.mpu9250.get_imu()
        
            # read IMU
            ax, ay, az = data['accel']
            gx, gy, gz = data['gyro']

            # compensate for turns
            theta = -math.atan2(az, ay) / (2 * math.pi)
            if (theta < 0 and self.theta > 0):
                if (self.theta - theta > self.threshold):
                    self.turns += 1
            elif (theta > 0 and self.theta < 0):
                if (theta - self.theta > self.threshold):
                    self.turns -= 1
            self.theta = theta

            # units (turns) and (1/s)
            self.buffer = (self.turns + theta, gx / 360)
        
        # call super
        return super().read()
                        
