# -*- coding: utf-8 -*-
"""
Support for BME280 temperature, humidity and pressure sensor.

"""
from time import sleep

from i2csense import I2cBaseClass


DEFAULT_I2C_ADDRESS = '0x76'
DEFAULT_OVERSAMPLING_TEMP = 1  # Temperature oversampling x 1
DEFAULT_OVERSAMPLING_PRES = 1  # Pressure oversampling x 1
DEFAULT_OVERSAMPLING_HUM = 1  # Humidity oversampling x 1
DEFAULT_OPERATION_MODE = 3  # Normal mode (forced mode: 2)
DEFAULT_T_STANDBY = 5  # Tstandby 5ms
DEFAULT_FILTER_MODE = 0  # Filter off
DEFAULT_DELTA_TEMP = 0.


class BME280(I2cBaseClass):
    """BME280 sensor working in i2C bus."""

    def __init__(self, bus,
                 i2c_address=DEFAULT_I2C_ADDRESS,
                 osrs_t=DEFAULT_OVERSAMPLING_TEMP,
                 osrs_p=DEFAULT_OVERSAMPLING_PRES,
                 osrs_h=DEFAULT_OVERSAMPLING_HUM,
                 mode=DEFAULT_OPERATION_MODE,
                 t_sb=DEFAULT_T_STANDBY,
                 filter_mode=DEFAULT_FILTER_MODE,
                 delta_temp=DEFAULT_DELTA_TEMP,
                 spi3w_en=0,  # 3-wire SPI Disable
                 logger=None):
        """Initialize the sensor handler."""
        I2cBaseClass.__init__(self, bus, i2c_address, logger)

        # BME280 parameters
        self.mode = mode
        self.ctrl_meas_reg = (osrs_t << 5) | (osrs_p << 2) | self.mode
        self.config_reg = (t_sb << 5) | (filter_mode << 2) | spi3w_en
        self.ctrl_hum_reg = osrs_h

        self._delta_temp = delta_temp
        self._with_pressure = osrs_p > 0
        self._with_humidity = osrs_h > 0

        # Calibration data
        self._calibration_t = None
        self._calibration_h = None
        self._calibration_p = None
        self._temp_fine = None

        # Sensor data
        self._temperature = None
        self._humidity = None
        self._pressure = None

        self.update(True)

    def _compensate_temperature(self, adc_t):
        """Compensate temperature.

        Formula from datasheet Bosch BME280 Environmental sensor.
        8.1 Compensation formulas in double precision floating point
        Edition BST-BME280-DS001-10 | Revision 1.1 | May 2015
        """
        var_1 = ((adc_t / 16384.0 - self._calibration_t[0] / 1024.0)
                 * self._calibration_t[1])
        var_2 = ((adc_t / 131072.0 - self._calibration_t[0] / 8192.0)
                 * (adc_t / 131072.0 - self._calibration_t[0] / 8192.0)
                 * self._calibration_t[2])
        self._temp_fine = var_1 + var_2
        if self._delta_temp != 0.:  # temperature correction for self heating
            temp = self._temp_fine / 5120.0 + self._delta_temp
            self._temp_fine = temp * 5120.0
        else:
            temp = self._temp_fine / 5120.0
        return temp

    def _compensate_pressure(self, adc_p):
        """Compensate pressure.

        Formula from datasheet Bosch BME280 Environmental sensor.
        8.1 Compensation formulas in double precision floating point
        Edition BST-BME280-DS001-10 | Revision 1.1 | May 2015.
        """
        var_1 = (self._temp_fine / 2.0) - 64000.0
        var_2 = ((var_1 / 4.0) * (var_1 / 4.0)) / 2048
        var_2 *= self._calibration_p[5]
        var_2 += ((var_1 * self._calibration_p[4]) * 2.0)
        var_2 = (var_2 / 4.0) + (self._calibration_p[3] * 65536.0)
        var_1 = (((self._calibration_p[2]
                   * (((var_1 / 4.0) * (var_1 / 4.0)) / 8192)) / 8)
                 + ((self._calibration_p[1] * var_1) / 2.0))
        var_1 /= 262144
        var_1 = ((32768 + var_1) * self._calibration_p[0]) / 32768

        if var_1 == 0:
            return 0

        pressure = ((1048576 - adc_p) - (var_2 / 4096)) * 3125
        if pressure < 0x80000000:
            pressure = (pressure * 2.0) / var_1
        else:
            pressure = (pressure / var_1) * 2

        var_1 = (self._calibration_p[8]
                 * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
        var_2 = ((pressure / 4.0) * self._calibration_p[7]) / 8192.0
        pressure += ((var_1 + var_2 + self._calibration_p[6]) / 16.0)

        return pressure / 100

    def _compensate_humidity(self, adc_h):
        """Compensate humidity.

        Formula from datasheet Bosch BME280 Environmental sensor.
        8.1 Compensation formulas in double precision floating point
        Edition BST-BME280-DS001-10 | Revision 1.1 | May 2015.
        """
        var_h = self._temp_fine - 76800.0
        if var_h == 0:
            return 0

        var_h = ((adc_h - (self._calibration_h[3] * 64.0 +
                           self._calibration_h[4] / 16384.0 * var_h))
                 * (self._calibration_h[1] / 65536.0
                    * (1.0 + self._calibration_h[5] / 67108864.0 * var_h
                       * (1.0 + self._calibration_h[2] / 67108864.0 * var_h))))
        var_h *= 1.0 - self._calibration_h[0] * var_h / 524288.0

        if var_h > 100.0:
            var_h = 100.0
        elif var_h < 0.0:
            var_h = 0.0

        return var_h

    def _populate_calibration_data(self):
        """Populate calibration data.

        From datasheet Bosch BME280 Environmental sensor.
        """
        calibration_t = []
        calibration_p = []
        calibration_h = []
        raw_data = []

        try:
            for i in range(0x88, 0x88 + 24):
                raw_data.append(self._bus.read_byte_data(self._i2c_add, i))
            raw_data.append(self._bus.read_byte_data(self._i2c_add, 0xA1))
            for i in range(0xE1, 0xE1 + 7):
                raw_data.append(self._bus.read_byte_data(self._i2c_add, i))
        except OSError as exc:
            if self._logger is not None:
                self._logger.error("Can't populate calibration data: %s", exc)
            else:
                print("Can't populate calibration data: %s", exc)
            return

        calibration_t.append((raw_data[1] << 8) | raw_data[0])
        calibration_t.append((raw_data[3] << 8) | raw_data[2])
        calibration_t.append((raw_data[5] << 8) | raw_data[4])

        if self._with_pressure:
            calibration_p.append((raw_data[7] << 8) | raw_data[6])
            calibration_p.append((raw_data[9] << 8) | raw_data[8])
            calibration_p.append((raw_data[11] << 8) | raw_data[10])
            calibration_p.append((raw_data[13] << 8) | raw_data[12])
            calibration_p.append((raw_data[15] << 8) | raw_data[14])
            calibration_p.append((raw_data[17] << 8) | raw_data[16])
            calibration_p.append((raw_data[19] << 8) | raw_data[18])
            calibration_p.append((raw_data[21] << 8) | raw_data[20])
            calibration_p.append((raw_data[23] << 8) | raw_data[22])

        if self._with_humidity:
            calibration_h.append(raw_data[24])
            calibration_h.append((raw_data[26] << 8) | raw_data[25])
            calibration_h.append(raw_data[27])
            calibration_h.append((raw_data[28] << 4) | (0x0F & raw_data[29]))
            calibration_h.append(
                (raw_data[30] << 4) | ((raw_data[29] >> 4) & 0x0F))
            calibration_h.append(raw_data[31])

        for i in range(1, 2):
            if calibration_t[i] & 0x8000:
                calibration_t[i] = (-calibration_t[i] ^ 0xFFFF) + 1

        if self._with_pressure:
            for i in range(1, 8):
                if calibration_p[i] & 0x8000:
                    calibration_p[i] = (-calibration_p[i] ^ 0xFFFF) + 1

        if self._with_humidity:
            for i in range(0, 6):
                if calibration_h[i] & 0x8000:
                    calibration_h[i] = (-calibration_h[i] ^ 0xFFFF) + 1

        self._calibration_t = calibration_t
        self._calibration_h = calibration_h
        self._calibration_p = calibration_p

    def _take_forced_measurement(self):
        """Take a forced measurement.

        In forced mode, the BME sensor goes back to sleep after each
        measurement and we need to set it to forced mode once at this point,
        so it will take the next measurement and then return to sleep again.
        In normal mode simply does new measurements periodically.
        """
        # set to forced mode, i.e. "take next measurement"
        self._bus.write_byte_data(self._i2c_add, 0xF4, self.ctrl_meas_reg)
        while self._bus.read_byte_data(self._i2c_add, 0xF3) & 0x08:
            sleep(0.005)

    def update(self, first_reading=False):
        """Read raw data and update compensated variables."""
        try:
            if first_reading or not self._ok:
                self._bus.write_byte_data(self._i2c_add, 0xF2,
                                          self.ctrl_hum_reg)
                self._bus.write_byte_data(self._i2c_add, 0xF5, self.config_reg)
                self._bus.write_byte_data(self._i2c_add, 0xF4,
                                          self.ctrl_meas_reg)
                self._populate_calibration_data()

            if self.mode == 2:  # MODE_FORCED
                self._take_forced_measurement()

            data = []
            for i in range(0xF7, 0xF7 + 8):
                data.append(self._bus.read_byte_data(self._i2c_add, i))
        except OSError as exc:
            if self._logger is not None:
                self._logger.warning("Bad update: %s", exc)
            else:
                print("Bad update: %s", exc)
            self._ok = False
            return

        pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        hum_raw = (data[6] << 8) | data[7]
        self._ok = False

        temperature = self._compensate_temperature(temp_raw)
        if (temperature >= -20) and (temperature < 80):
            self._temperature = temperature
            self._ok = True
        if self._with_humidity:
            humidity = self._compensate_humidity(hum_raw)
            if (humidity >= 0) and (humidity <= 100):
                self._humidity = humidity
            else:
                self._ok = False
        if self._with_pressure:
            pressure = self._compensate_pressure(pres_raw)
            if pressure > 100:
                self._pressure = pressure
            else:
                self._ok = False

    @property
    def temperature(self):
        """Return temperature in celsius."""
        return self._temperature

    @property
    def humidity(self):
        """Return relative humidity in percentage."""
        return self._humidity

    @property
    def pressure(self):
        """Return pressure in hPa."""
        return self._pressure
