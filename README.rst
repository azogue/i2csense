Another library to handle sensors connected via
**I2c bus** (SDA, SCL pins) to the **Raspberry Pi**.

This library implements the following i2c sensors:
- **`Bosch BME280 Environmental sensor (temperature, humidity and pressure) <https://cdn-shop.adafruit.com/datasheets/BST-BME280_DS001-10.pdf>`_**
- **`HTU21D temperature and humidity sensor <http://www.datasheetspdf.com/PDF/HTU21D/779951/1>`_**
- **`BH1750FVI light level sensor <http://cpre.kmutnb.ac.th/esl/learning/bh1750-light-sensor/bh1750fvi-e_datasheet.pdf>`_**

Installation
------------

This library needs the **i2c bus** to be enabled, and uses the
``smbus-cffi`` module to communicate with it, so, before installing with
``pip``, make sure the bus is enabled, and the necessary dependencies
are available:

Directions for installing smbus support on Raspberry Pi:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable I2c interface with the Raspberry Pi config utility:

.. code:: bash

    # Enable i2c interface
    sudo raspi-config

Select ``Interfacing options->I2C`` choose ``<Yes>`` and hit ``Enter``,
then go to ``Finish`` and you'll be prompted to reboot.

Install dependencies for use the ``smbus-cffi`` module and reboot:

.. code:: bash

    sudo apt-get install build-essential libi2c-dev i2c-tools python-dev libffi-dev
    sudo reboot

Check the i2c address of the sensors
                                    

After installing ``i2c-tools``, a new utility is available to scan the
addresses of the connected sensors:

.. code:: bash

    /usr/sbin/i2cdetect -y 1

It will output a table like this:

.. code:: text

         0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
    00:          -- -- -- -- -- -- -- -- -- -- -- -- --
    10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- 23 -- -- -- -- -- -- -- -- -- -- -- --
    30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    70: -- -- -- -- -- -- -- 77

So you can see three sensors are present at **0x23 (BH1750)**, **0x40
(HTU21D)** and **0x77 (BME280)** addresses.

Install with pip
~~~~~~~~~~~~~~~~

Finally, in your python environment,

.. code:: bash

    pip install i2csense

Usage
-----

This library is intended to be used by other applications, where sensors
are instantiated with their configuration parameters, to be read at the
desired intervals. However, if you want to use as a simple logger via
command line, a simple CLI is also available to test the sensors.

.. code:: python

    import smbus
    from i2csense.bme280 import BME280

    bus = smbus.Bus(1)
    sensor = BME280(bus)
    delta_secs = 5

    while True:
        sensor.update()
        if not sensor.sample_ok:
            print("An error has occured")
            break
        print(sensor.current_state_str)
        sleep(delta_secs)

**CLI usage**

Find sensors:

.. code:: bash

    i2csense
    # or specify the i2c bus:
    i2csense -b 0

Test sensors:

.. code:: bash

    # Test BME280 sensor with default params:
    i2csense -s bme280

    # Test BME280 sensor with custom params every 10 secs:
    i2csense -d 10 --bus 0 --address 0x77 --sensor bme280 --params osrs_t=4 osrs_p=4 osrs_h=4 mode=2 filter_mode=1

Changelog
---------

-  **v0.0.1**: First release with 3 sensors: **BME280, BH1750, HTU21D**.
-  **v0.0.2**: Minor fixes.
-  **v0.0.3**: Minor fixes for `BH1750`, fix `README.rst`.

TODO:
-----

-  **Append more sensors**.
-  finish CLI interface with better help and more configuration options.

Although the library only covers three sensors, it would be ideal to
continue completing it with more sensors or actuators running in the i2c
bus, so I encourage you to contribute with more sensors, or to copy,
change, edit, or suggest any changes.
