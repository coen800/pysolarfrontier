"""Solart Frontier Inverter interface."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import date, datetime
import logging
from typing import Any

import pysolarfrontier
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.start import async_at_start
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

MIN_INTERVAL = 60
MAX_INTERVAL = 500

SF_UNIT_MAPPINGS = {
    "": None,
    "MWh": UnitOfEnergy.MEGA_WATT_HOUR,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
    "W": UnitOfPower.WATT,
}


PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_HOST): cv.string, vol.Optional(CONF_NAME): cv.string}
)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Solar Frontier sensors."""

    remove_interval_update = None
    
    # Init all sensors
    sensor_def = pysolarfrontier.Sensors()
    
    # Use all sensors by default
    hass_sensors: list[SFsensor] = []
    #hass_sensors = []

    try:
        pysf = pysolarfrontier.SF(config[CONF_HOST])
        done = await pysf.read(sensor_def)
    except (pysolarfrontier.UnexpectedResponseException) as err:
        _LOGGER.error(
            "Unexpected response received from Solar Frontier. " "Original error: %s",
            err,
        )
        return
    except (pysolarfrontier.ConnectionErrorException) as err:
        _LOGGER.error(
            "Error in Solar Frontier, please check host/ip address. "
            "Original error: %s",
            err,
        )
        return

    if not done:
        raise PlatformNotReady

    for sensor in sensor_def:
        if sensor.name == "total_yield":
            continue
        if sensor.enabled:
            hass_sensors.append(SFsensor(sensor, inverter_name=config.get(CONF_NAME)))

    async_add_entities(hass_sensors)

    async def async_sf() -> bool:
        """Update all the Solar Frontier sensors."""
        values = await pysf.read(sensor_def)

        for sensor in hass_sensors:
            sensor.async_update_values()

        return values

    @callback
    def start_update_interval(hass: HomeAssistant) -> None:
        """Start the update interval scheduling."""
        nonlocal remove_interval_update
        remove_interval_update = async_track_time_interval_backoff(hass, async_sf)

    @callback
    def stop_update_interval(event):
        """Properly cancel the scheduled update."""
        remove_interval_update()

    hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, stop_update_interval)
    async_at_start(hass, start_update_interval)


@callback
def async_track_time_interval_backoff(
    hass: HomeAssistant, action: Callable[[], Coroutine[Any, Any, bool]]
) -> CALLBACK_TYPE:
    """Add a listener that fires repetitively and increases the interval when failed."""
    remove = None
    interval = MIN_INTERVAL

    async def interval_listener(now: datetime | None = None) -> None:
        """Handle elapsed interval with backoff."""
        nonlocal interval, remove
        try:
            if await action():
                interval = MIN_INTERVAL
            else:
                interval = min(interval * 2, MAX_INTERVAL)
        finally:
            remove = async_call_later(hass, interval, interval_listener)

    hass.async_create_task(interval_listener())

    def remove_listener() -> None:
        """Remove interval listener."""
        if remove:
            remove()

    return remove_listener


class SFsensor(SensorEntity):
    """Representation of a Solar Frontier sensor."""

    def __init__(
        self,
        pysf_sensor,
        inverter_name=None
        ):
        """Initialize the Solar Frontier sensor."""
        self._sensor = pysf_sensor
        self._inverter_name = inverter_name
        self._state = self._sensor.value

        if pysf_sensor.name in ("today_yield", "month_yield", "year_yield"):
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            #self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        if pysf_sensor.name == "total_yield":
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            #self._attr_last_reset = dt_util.utc_from_timestamp(0)
        
        native_uom = SF_UNIT_MAPPINGS[pysf_sensor.unit]
        self._attr_native_unit_of_measurement = native_uom
        if self._inverter_name:
            self._attr_name = f"{self._inverter_name}_{pysf_sensor.name}"
        else:
            self._attr_name = f"{pysf_sensor.name}"
        if native_uom == UnitOfPower.WATT:
            self._attr_device_class = SensorDeviceClass.POWER
        if native_uom == UnitOfEnergy.KILO_WATT_HOUR:
            self._attr_device_class = SensorDeviceClass.ENERGY
        if native_uom == UnitOfEnergy.MEGA_WATT_HOUR:
            self._attr_device_class = SensorDeviceClass.ENERGY


    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def per_day_basis(self) -> bool:
        """Return if the sensors value is on daily basis or not."""
        return self._sensor.per_day_basis

    @property
    def per_total_basis(self) -> bool:
        """Return if the sensors value is cumulative or not."""
        return self._sensor.per_total_basis

    @property
    def date_updated(self) -> date:
        """Return the date when the sensor was last updated."""
        return self._sensor.date

    @callback
    def async_update_values(self, unknown_state=False):
        """Update this sensor."""
        update = False

        if self._sensor.value != self._state:
            update = True
            self._state = self._sensor.value

        if unknown_state and self._state is not None:
            update = True
            self._state = None

        if update:
            self.async_write_ha_state()
