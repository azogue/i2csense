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
from codecs import open
import os
from setuptools import setup, find_packages
from i2csense import __version__ as version


packages = find_packages()
basedir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(basedir, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='i2csense',
    version=version,
    description='A library to handle i2c sensors with the Raspberry Pi',
    long_description='\n' + long_description,
    keywords='raspberry i2c sensors python3 bme280 bh1750 htu21d',
    author='Eugenio Panadero',
    author_email='eugenio.panadero@gmail.com',
    url='https://github.com/azogue/i2csense',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Topic :: Home Automation',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: Unix'],
    packages=packages,
    install_requires=['smbus-cffi==0.5.1'],
    entry_points={
        'console_scripts': ['i2csense = i2csense.__main__:main_cli']
    },
)
