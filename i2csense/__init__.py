# -*- coding: utf-8 -*-
"""
Another library to handle sensors connected via I2c bus (SDA, SCL pins) to your
Raspberry Pi.

This library implements the following i2c sensors:
- Bosch BME280 Environmental sensor (temperature, humidity and pressure)
  Datasheet: https://cdn-shop.adafruit.com/datasheets/BST-BME280_DS001-10.pdf
- HTU21D temperature and humidity sensor
  Datasheet: http://www.datasheetspdf.com/PDF/HTU21D/779951/1
- BH1750FVI light level sensor
  Datasheet: http://cpre.kmutnb.ac.th/esl/learning/
             bh1750-light-sensor/bh1750fvi-e_datasheet.pdf

This library needs the i2c bus to be enabled, and uses the `smbus-cffi`
module to communicate with it, so, before installing with `pip`, make sure
the bus is enabled, and the necessary dependencies are available:
    `build-essential libi2c-dev i2c-tools python-dev libffi-dev`

This library is intended to be used by other applications, where sensors are
instantiated with their configuration parameters, to be read at the desired
intervals.
"""
from math import log10


__version__ = '0.0.3'

DEFAULT_I2C_BUS = 1
DEFAULT_DELAY_SEC = 5


class I2cVariableNotImplemented(Exception):
    """Sensor variable is not present in this instance."""

    def __init__(self, *args, **kwargs):  # real signature unknown
        pass


class I2cBaseClass(object):
    """Base class for sensors working in i2C bus."""

    def __init__(self, bus_handler, i2c_address, logger=None):
        """Init the sensor direction."""
        self._bus = bus_handler
        self._i2c_add = int(i2c_address, 0)
        self._ok = False
        self._logger = logger

    def __repr__(self):
        """String representation of the i2c sensor"""
        return "<I2c sensor at %s. Current state: %s>" % (
            hex(self._i2c_add), self.current_state_str)

    def update(self):
        """Read sensor data and update state and variables."""
        raise NotImplementedError

    @property
    def sample_ok(self):
        """Return sensor ok state."""
        return self._ok

    @property
    def temperature(self):
        """Return temperature in celsius."""
        raise I2cVariableNotImplemented

    @property
    def humidity(self):
        """Return relative humidity in percentage."""
        raise I2cVariableNotImplemented

    @property
    def pressure(self):
        """Return pressure in hPa."""
        raise I2cVariableNotImplemented

    @property
    def light_level(self):
        """Return light level in lux."""
        raise I2cVariableNotImplemented

    def _get_value_opc_attr(self, attr_name, prec_decimals=2):
        """Return sensor attribute with precission, or None if not present."""
        try:
            value = getattr(self, attr_name)
            if value is not None:
                return round(value, prec_decimals)
        except I2cVariableNotImplemented:
            pass
        return None

    @property
    def current_state_str(self):
        """Return string representation of the current state of the sensor."""
        if self.sample_ok:
            msg = ''
            temperature = self._get_value_opc_attr('temperature')
            if temperature is not None:
                msg += 'Temp: %s ºC, ' % temperature
            humidity = self._get_value_opc_attr('humidity')
            if humidity is not None:
                msg += 'Humid: %s %%, ' % humidity
            pressure = self._get_value_opc_attr('pressure')
            if pressure is not None:
                msg += 'Press: %s mb, ' % pressure
            light_level = self._get_value_opc_attr('light_level')
            if light_level is not None:
                msg += 'Light: %s lux, ' % light_level
            return msg[:-2]
        else:
            return "Bad sample"

    @property
    def dew_point_temperature(self):
        """Return the dew point temperature in ºC for the last measurement.

        For sensors implementing temperature and humidity values.
        Extracted from the HTU21D sensor spec sheet."""
        if self.sample_ok:
            temperature = self._get_value_opc_attr('temperature', 3)
            humidity = self._get_value_opc_attr('humidity', 3)
            if temperature is not None and humidity is not None:
                # Calc dew point temperature in celsius
                coef_a, coef_b, coef_c = 8.1332, 1762.39, 235.66
                part_press = 10 ** (coef_a - coef_b / (temperature + coef_c))
                dewp = - coef_c
                dewp -= coef_b / (log10(humidity * part_press / 100.) - coef_a)
                return dewp
        return None
