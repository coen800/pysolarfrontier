# PySolarFrontier
PySolarFrontier interacts as a library to communicate with Solar Frontier inverters.

I created this library to use it in the Solar Frontier Inverter integration made for Home Assistant.

Confirmed to work with the SF-WR-3000 inverter.

Credits to [fredericvl and his pysaj library](https://github.com/fredericvl/pysaj), alot of the code is based on his library.

# Example usage
Customize based on your needs.
```python
#!/usr/bin/env python3
import pysolarfrontier as pysf
import asyncio

INVERTER_IP = 'x.x.x.x'

async def example():
    # Initiate sensors
    sensor_def = pysf.Sensors()
    # Define IP of the inverter
    sf = pysf.SF(INVERTER_IP)
    # Get sensor values
    await sf.read(sensor_def)
    # Print sensor values
    for sensor in sensor_def:
        print()
        print('key:             ', sensor.key)
        print('name:            ', sensor.name)
        print('unit:            ', sensor.unit)
        print('value:           ', sensor.value)
        print('per_day_basis:   ', sensor.per_day_basis)
        print('per_total_basis: ', sensor.per_total_basis)
        print('date:            ', sensor.date)
        print('enabled:         ', sensor.enabled)

asyncio.run(example
```
