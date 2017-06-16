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
  Datasheet: http://cpre.kmutnb.ac.th/esl/learning/bh1750-light-sensor
  /bh1750fvi-e_datasheet.pdf

This library needs the i2c bus to be enabled, and uses the `smbus-cffi`
module to communicate with it, so, before installing with `pip`, make sure
the bus is enabled, and the necessary dependencies are available:
    `build-essential libi2c-dev i2c-tools python-dev libffi-dev`

This library is intended to be used by other applications, where sensors are
instantiated with their configuration parameters, to be read at the desired
intervals.

# CLI interface to test the i2c sensors

"""
import argparse
import sys

from i2csense import DEFAULT_DELAY_SEC, DEFAULT_I2C_BUS
from i2csense.bme280 import BME280, DEFAULT_I2C_ADDRESS as I2C_ADD_BME280
from i2csense.bh1750 import BH1750, DEFAULT_I2C_ADDRESS as I2C_ADD_BH1750
from i2csense.htu21d import HTU21D, I2C_ADDRESS as I2C_ADD_HTU21D


SENSORS = {'bme280': (BME280, I2C_ADD_BME280),
           'htu21d': (HTU21D, I2C_ADD_HTU21D),
           'bh1750': (BH1750, I2C_ADD_BH1750)}


def _cli_argument_parser():
    p = argparse.ArgumentParser(description="CLI to test i2c sensors")
    p.add_argument('-b', '--bus', action='store', type=int, metavar='B',
                   default=DEFAULT_I2C_BUS,
                   help="Set the i2c bus number. Default is 1")
    p.add_argument('-s', '--sensor', action='store', metavar='S',
                   help="Set the type of i2c sensor to test. Valid sensors "
                        "are: {}".format(', '.join(SENSORS.keys())))
    p.add_argument('-a', '--address', action='store', type=str, metavar='A',
                   help="Set a specific i2c address for the sensor")
    p.add_argument('-p', '--params', action='store', nargs='*', metavar='P',
                   help="Set specific params to customise the sensor "
                        "working mode. Use key=value pairs.")
    p.add_argument('-d', '--delay', action='store', type=int, metavar='D',
                   default=DEFAULT_DELAY_SEC,
                   help="Set the delay between samples in the infinite loop")
    return p.parse_args()


def main_cli():
    """CLI minimal interface."""
    # Get params
    args = _cli_argument_parser()
    delta_secs = args.delay
    i2cbus = args.bus
    i2c_address = args.address
    sensor_key = args.sensor
    sensor_params = args.params
    params = {}
    if sensor_params:
        def _parse_param(str_param):
            key, value = str_param.split('=')
            try:
                value = int(value)
            except ValueError:
                pass
            return {key.strip(): value}

        [params.update(_parse_param(sp)) for sp in sensor_params]

    if sensor_key:
        from time import sleep
        # Bus init
        try:
            # noinspection PyUnresolvedReferences
            import smbus
            bus_handler = smbus.SMBus(i2cbus)
        except ImportError as exc:
            print(exc, "\n", "Please install smbus-cffi before.")
            sys.exit(-1)

        # Sensor selection
        try:
            sensor_handler, i2c_default_address = SENSORS[sensor_key]
        except KeyError:
            print("'%s' is not recognized as an implemented i2c sensor."
                  % sensor_key)
            sys.exit(-1)

        if i2c_address:
            i2c_address = hex(int(i2c_address, 0))
        else:
            i2c_address = i2c_default_address

        # Sensor init
        sensor = sensor_handler(bus_handler, i2c_address, **params)

        # Infinite loop
        try:
            while True:
                sensor.update()
                if not sensor.sample_ok:
                    print("An error has occured.")
                    break
                print(sensor.current_state_str)
                sleep(delta_secs)
        except KeyboardInterrupt:
            print("Bye!")
    else:
        # Run detection mode
        from subprocess import check_output
        cmd = '/usr/sbin/i2cdetect -y {}'.format(i2cbus)
        try:
            output = check_output(cmd.split())
            print("Running i2cdetect utility in i2c bus {}:\n"
                  "The command '{}' has returned:\n{}"
                  .format(i2cbus, cmd, output.decode()))
        except FileNotFoundError:
            print("Please install i2cdetect before.")
            sys.exit(-1)

        # Parse output
        addresses = ['0x' + l for line in output.decode().splitlines()[1:]
                     for l in line.split()[1:] if l != '--']
        if addresses:
            print("{} sensors detected in {}"
                  .format(len(addresses), ', '.join(addresses)))
        else:
            print("No i2c sensors detected.")


if __name__ == '__main__':
    main_cli()
