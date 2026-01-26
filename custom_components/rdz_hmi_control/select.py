"""Select platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ZONE_NAME,
    CONF_ZONES,
    DATA_ZONE_MODES,
    DOMAIN,
    ZONE_MODE_MAN,
    ZONE_MODE_OFF,
    ZONE_MODE_OPTIONS,
    ZONE_MODE_PGM,
    ZONE_MODE_PGM_MAN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Reverse mapping from option string to mode value
ZONE_MODE_VALUES = {v: k for k, v in ZONE_MODE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI zone mode select entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones_config = config_entry.data.get(CONF_ZONES, {})

    entities = []
    for zone_id_str, zone_data in zones_config.items():
        zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
        entities.append(RDZZoneModeSelect(coordinator, zone_id, zone_data))

    async_add_entities(entities)


class RDZZoneModeSelect(CoordinatorEntity[RDZDataUpdateCoordinator], SelectEntity):
    """Representation of an RDZ HMI zone mode select entity."""

    _attr_has_entity_name = True
    _attr_options = list(ZONE_MODE_OPTIONS.values())

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the zone mode select entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data

        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.client.host}_{zone_id}_zone_mode"
        )
        self._attr_translation_key = "zone_mode"
        self._attr_name = "Zone mode"

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
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if self.coordinator.data is None:
            return None

        zone_modes = self.coordinator.data.get(DATA_ZONE_MODES, {})
        mode_value = zone_modes.get(self._zone_id)

        if mode_value is None:
            return None

        return ZONE_MODE_OPTIONS.get(mode_value, ZONE_MODE_OPTIONS[ZONE_MODE_OFF])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode_value = ZONE_MODE_VALUES.get(option)

        if mode_value is None:
            _LOGGER.error("Invalid zone mode option: %s", option)
            return

        success = await self.coordinator.async_set_zone_mode(self._zone_id, mode_value)
        if not success:
            _LOGGER.error("Failed to set zone mode for zone %d", self._zone_id)

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
