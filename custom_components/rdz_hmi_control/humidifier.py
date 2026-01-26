"""Humidifier platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONES,
    DATA_DEHUMIDIFICATION_SETPOINTS,
    DATA_HUMIDITY,
    DOMAIN,
    MAX_HUMIDITY,
    MIN_HUMIDITY,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI dehumidifier entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones_config = config_entry.data.get(CONF_ZONES, {})

    entities = []
    for zone_id_str, zone_data in zones_config.items():
        zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
        entities.append(RDZDehumidifierEntity(coordinator, zone_id, zone_data))

    async_add_entities(entities)


class RDZDehumidifierEntity(
    CoordinatorEntity[RDZDataUpdateCoordinator], HumidifierEntity
):
    """Representation of an RDZ HMI dehumidifier entity."""

    _attr_has_entity_name = True
    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature(0)
    _attr_min_humidity = MIN_HUMIDITY
    _attr_max_humidity = MAX_HUMIDITY

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the dehumidifier entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data

        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.client.host}_{zone_id}_dehumidifier"
        )
        self._attr_translation_key = "dehumidifier"
        self._attr_name = "Dehumidifier"

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
    def is_on(self) -> bool:
        """Return True if the dehumidifier is on.

        The dehumidifier is always considered 'on' as it's system-controlled.
        """
        return True

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity."""
        if self.coordinator.data is None:
            return None

        humidity_data = self.coordinator.data.get(DATA_HUMIDITY, {})
        return humidity_data.get(self._zone_id)

    @property
    def target_humidity(self) -> float | None:
        """Return the target humidity (dehumidification setpoint)."""
        if self.coordinator.data is None:
            return None

        setpoints = self.coordinator.data.get(DATA_DEHUMIDIFICATION_SETPOINTS, {})
        return setpoints.get(self._zone_id)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the target humidity (dehumidification setpoint)."""
        success = await self.coordinator.async_set_dehumidification_setpoint(
            self._zone_id, float(humidity)
        )
        if not success:
            _LOGGER.error(
                "Failed to set dehumidification setpoint for zone %d", self._zone_id
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the dehumidifier.

        The dehumidifier is system-controlled, so this is a no-op.
        """
        _LOGGER.debug(
            "Dehumidifier turn_on called for zone %d, but system is auto-controlled",
            self._zone_id,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the dehumidifier.

        The dehumidifier is system-controlled, so this is a no-op.
        """
        _LOGGER.debug(
            "Dehumidifier turn_off called for zone %d, but system is auto-controlled",
            self._zone_id,
        )

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
            self.coordinator.config_entry.add_update_listener(
                self._async_config_entry_updated
            )
        )

    async def _async_config_entry_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle config entry update."""
        self._update_device_info()
        self.async_write_ha_state()
