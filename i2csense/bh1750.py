# -*- coding: utf-8 -*-
"""
Support for BH1750 light level sensor.
"""
from time import sleep

from i2csense import I2cBaseClass


# Operation modes for BH1750 sensor (from the datasheet). Time typically 120ms
# In one time measurements, device is set to Power Down after each sample.
CONTINUOUS_LOW_RES_MODE = "continuous_low_res_mode"
CONTINUOUS_HIGH_RES_MODE_1 = "continuous_high_res_mode_1"
CONTINUOUS_HIGH_RES_MODE_2 = "continuous_high_res_mode_2"
ONE_TIME_HIGH_RES_MODE_1 = "one_time_high_res_mode_1"
ONE_TIME_HIGH_RES_MODE_2 = "one_time_high_res_mode_2"
ONE_TIME_LOW_RES_MODE = "one_time_low_res_mode"
OPERATION_MODES = {
    CONTINUOUS_LOW_RES_MODE: (0x13, True),      # 4lx resolution
    CONTINUOUS_HIGH_RES_MODE_1: (0x10, True),   # 1lx resolution.
    CONTINUOUS_HIGH_RES_MODE_2: (0X11, True),   # 0.5lx resolution.
    ONE_TIME_LOW_RES_MODE: (0x23, False),       # 4lx resolution.
    ONE_TIME_HIGH_RES_MODE_1: (0x20, False),    # 1lx resolution.
    ONE_TIME_HIGH_RES_MODE_2: (0x21, False),    # 0.5lx resolution.
}

DEFAULT_I2C_ADDRESS = '0x23'
DEFAULT_MODE = CONTINUOUS_HIGH_RES_MODE_1
DEFAULT_DELAY_MS = 120
DEFAULT_SENSITIVITY = 69                        # sensitivity from 31 to 254

# Define some constants from the datasheet
POWER_DOWN = 0x00  # No active state
POWER_ON = 0x01  # Power on
RESET = 0x07  # Reset data register value


class BH1750(I2cBaseClass):
    """Implement BH1750 communication."""

    def __init__(self, bus, i2c_address=DEFAULT_I2C_ADDRESS,
                 operation_mode=DEFAULT_MODE,
                 measurement_delay=DEFAULT_DELAY_MS,
                 sensitivity=DEFAULT_SENSITIVITY,
                 logger=None):
        """Initialize the sensor."""
        I2cBaseClass.__init__(self, bus, i2c_address, logger)

        self._mode = None
        self._delay = measurement_delay / 1000.
        self._operation_mode = OPERATION_MODES[operation_mode][0]
        self._continuous_sampling = OPERATION_MODES[operation_mode][1]
        self._high_res = (self._operation_mode & 0x03) == 0x01
        self._low_res = (self._operation_mode & 0x03) == 0x03
        self._mtreg = None

        self._power_down()
        self.set_sensitivity(sensitivity)

        self._light_level = -1
        self.update()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shut down the sensor at exit."""
        self._power_down()

    def _set_mode(self, mode):
        self._mode = mode
        try:
            self._bus.write_byte(self._i2c_add, self._mode)
            self._ok = True
        except OSError as exc:
            if self._logger is not None:
                self._logger.error("Bad writing in bus: %s", exc)
            else:
                print("Bad writing in bus: %s", exc)
            self._ok = False

    def _power_down(self):
        self._set_mode(POWER_DOWN)

    def _power_on(self):
        self._set_mode(POWER_ON)

    def _reset(self):
        # It has to be powered on before resetting
        self._power_on()
        self._set_mode(RESET)

    @property
    def sensitivity(self) -> int:
        """Return the sensitivity value, an integer between 31 and 254."""
        return self._mtreg

    def set_sensitivity(self, sensitivity=DEFAULT_SENSITIVITY):
        """Set the sensitivity value.

        Valid values are 31 (lowest) to 254 (highest), default is 69.
        """
        if sensitivity < 31:
            self._mtreg = 31
        elif sensitivity > 254:
            self._mtreg = 254
        else:
            self._mtreg = sensitivity
        self._power_on()
        self._set_mode(0x40 | (self._mtreg >> 5))
        self._set_mode(0x60 | (self._mtreg & 0x1f))
        self._power_down()

    def _get_result(self) -> float:
        """Return current measurement result in lx."""
        try:
            data = self._bus.read_word_data(self._i2c_add, self._mode)
            self._ok = True
        except OSError as exc:
            if self._logger is not None:
                self._logger.error("Bad reading in bus: %s", exc)
            else:
                print("Bad reading in bus: %s", exc)
            self._ok = False
            return -1

        count = data >> 8 | (data & 0xff) << 8
        mode2coeff = 2 if self._high_res else 1
        ratio = 1 / (1.2 * (self._mtreg / 69.0) * mode2coeff)
        return ratio * count

    def _wait_for_result(self):
        """Wait for the sensor to be ready for measurement."""
        basetime = 0.018 if self._low_res else 0.128
        sleep(basetime * (self._mtreg / 69.0) + self._delay)

    def update(self):
        """Update the measured light level in lux."""
        if not self._continuous_sampling \
                or self._light_level < 0 \
                or self._operation_mode != self._mode:
            self._reset()
            self._set_mode(self._operation_mode)
            self._wait_for_result()
        self._light_level = self._get_result()
        if not self._continuous_sampling:
            self._power_down()

    @property
    def light_level(self):
        """Return light level in lux."""
        return round(self._light_level, 1 if self._high_res else 0)
