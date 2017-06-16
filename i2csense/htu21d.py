# -*- coding: utf-8 -*-
"""
Support for HTU21D temperature and humidity sensor.

"""
from time import sleep

from i2csense import I2cBaseClass


I2C_ADDRESS = '0x40'

# Byte codes from the data sheet
CMD_READ_TEMP_HOLD = 0xE3
CMD_READ_HUM_HOLD = 0xE5
CMD_READ_TEMP_NOHOLD = 0xF3
CMD_READ_HUM_NOHOLD = 0xF5
CMD_WRITE_USER_REG = 0xE6
CMD_READ_USER_REG = 0xE7
CMD_SOFT_RESET = 0xFE
MEASUREMENT_WAIT_TIME = 0.055


class HTU21D(I2cBaseClass):
    """Implement HTU21D communication."""

    def __init__(self, bus, logger=None):
        """Initialize the sensor handler."""
        I2cBaseClass.__init__(self, bus, I2C_ADDRESS, logger)

        self._temperature = -255
        self._humidity = -255
        self._ok = self._soft_reset()

        if self._ok:
            self.update()

    def _soft_reset(self):
        try:
            self._bus.write_byte(self._i2c_add, CMD_SOFT_RESET)
            sleep(MEASUREMENT_WAIT_TIME)
            return True
        except OSError as exc:
            if self._logger is not None:
                self._logger.error("Bad writing in bus: %s", exc)
            else:
                print("Bad writing in bus: %s", exc)
            return False

    @staticmethod
    def _calc_temp(sensor_temp):
        t_sensor_temp = sensor_temp / 65536.0
        return -46.85 + (175.72 * t_sensor_temp)

    @staticmethod
    def _calc_humid(sensor_humid):
        t_sensor_humid = sensor_humid / 65536.0
        return -6.0 + (125.0 * t_sensor_humid)

    @staticmethod
    def _temp_coefficient(rh_actual, temp_actual):
        return rh_actual - 0.15 * (25 - temp_actual)

    @staticmethod
    def _crc8check(value):
        # Ported from Sparkfun Arduino HTU21D Library:
        # https://github.com/sparkfun/HTU21D_Breakout
        remainder = ((value[0] << 8) + value[1]) << 8
        remainder |= value[2]

        # POLYNOMIAL = 0x0131 = x^8 + x^5 + x^4 + 1
        # divisor = 0x988000 is the 0x0131 polynomial shifted to farthest
        # left of three bytes
        divisor = 0x988000

        for i in range(0, 16):
            if remainder & 1 << (23 - i):
                remainder ^= divisor
            divisor >>= 1

        if remainder == 0:
            return True
        return False

    @property
    def sample_ok(self):
        """Return True for a valid measurement data."""
        return self._ok and self._temperature > -100 and self._humidity > -1

    def update(self):
        """Read raw data and calculate temperature and humidity."""
        try:
            self._bus.write_byte(self._i2c_add, CMD_READ_TEMP_NOHOLD)
            sleep(MEASUREMENT_WAIT_TIME)
            buf_t = self._bus.read_i2c_block_data(
                self._i2c_add, CMD_READ_TEMP_HOLD, 3)

            self._bus.write_byte(self._i2c_add, CMD_READ_HUM_NOHOLD)
            sleep(MEASUREMENT_WAIT_TIME)
            buf_h = self._bus.read_i2c_block_data(
                self._i2c_add, CMD_READ_HUM_HOLD, 3)
        except OSError as exc:
            self._ok = False
            if self._logger is not None:
                self._logger.error("Bad reading: %s", exc)
            else:
                print("Bad reading: %s", exc)
            return

        if self._crc8check(buf_t):
            temp = (buf_t[0] << 8 | buf_t[1]) & 0xFFFC
            self._temperature = self._calc_temp(temp)

            if self._crc8check(buf_h):
                humid = (buf_h[0] << 8 | buf_h[1]) & 0xFFFC
                rh_actual = self._calc_humid(humid)
                # For temperature coefficient compensation
                rh_final = self._temp_coefficient(rh_actual, self._temperature)
                rh_final = 100.0 if rh_final > 100 else rh_final  # Clamp > 100
                rh_final = 0.0 if rh_final < 0 else rh_final  # Clamp < 0
                self._humidity = rh_final
            else:
                self._humidity = -255
                self._ok = False
        else:
            self._temperature = -255
            self._ok = False
            if self._logger is not None:
                self._logger.error("Bad CRC error")
            else:
                print("Bad CRC error")

    @property
    def temperature(self):
        """Return temperature in celsius."""
        return self._temperature

    @property
    def humidity(self):
        """Return relative humidity in percentage."""
        return self._humidity
