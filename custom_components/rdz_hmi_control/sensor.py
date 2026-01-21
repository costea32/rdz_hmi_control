"""Sensor platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONES,
    DATA_SUMMER_SETPOINTS,
    DATA_WINTER_SETPOINTS,
    DOMAIN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI sensor entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones_config = config_entry.data.get(CONF_ZONES, {})

    entities = []
    for zone_id_str, zone_data in zones_config.items():
        zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
        # Create winter and summer setpoint sensors for each zone
        entities.append(
            RDZSetpointSensor(coordinator, zone_id, zone_data, "winter")
        )
        entities.append(
            RDZSetpointSensor(coordinator, zone_id, zone_data, "summer")
        )

    async_add_entities(entities)


class RDZSetpointSensor(CoordinatorEntity[RDZDataUpdateCoordinator], SensorEntity):
    """Representation of an RDZ HMI setpoint sensor."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict[str, Any],
        setpoint_type: str,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data
        self._setpoint_type = setpoint_type  # "winter" or "summer"

        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.client.host}_{zone_id}_{setpoint_type}_setpoint"
        )

        if setpoint_type == "winter":
            self._attr_translation_key = "winter_setpoint"
            self._attr_name = "Winter setpoint"
        else:
            self._attr_translation_key = "summer_setpoint"
            self._attr_name = "Summer setpoint"

        self._update_device_info()

    def _update_device_info(self) -> None:
        """Update device info from zone data."""
        zones_config = self.coordinator.config_entry.data.get(CONF_ZONES, {})
        zone_data = zones_config.get(str(self._zone_id), self._zone_data)
        self._zone_data = zone_data

        zone_name = zone_data.get(CONF_ZONE_NAME, f"Zone {self._zone_id}")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.client.host}_{self._zone_id}")},
            name=zone_name,
            manufacturer="RDZ",
            model="HMI Thermostat",
            sw_version="1.0",
        )

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None

        if self._setpoint_type == "winter":
            setpoints = self.coordinator.data.get(DATA_WINTER_SETPOINTS, {})
        else:
            setpoints = self.coordinator.data.get(DATA_SUMMER_SETPOINTS, {})

        return setpoints.get(self._zone_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_device_info()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Listen for config entry updates
        self.async_on_remove(
            self.coordinator.config_entry.add_update_listener(self._async_config_entry_updated)
        )

    async def _async_config_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle config entry update."""
        self._update_device_info()
        self.async_write_ha_state()
