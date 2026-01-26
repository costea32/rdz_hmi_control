"""Number platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_TIME_SETTINGS,
    DOMAIN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Time setting configurations: (key, name, min, max)
TIME_SETTINGS = [
    ("day", "Day", 1, 31),
    ("month", "Month", 1, 12),
    ("year", "Year", 2000, 2099),
    ("hour", "Hour", 0, 23),
    ("minute", "Minute", 0, 59),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI number entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NumberEntity] = []

    # Add time setting number entities
    for key, name, min_val, max_val in TIME_SETTINGS:
        entities.append(
            RDZTimeSettingNumber(coordinator, key, name, min_val, max_val)
        )

    async_add_entities(entities)


class RDZTimeSettingNumber(CoordinatorEntity[RDZDataUpdateCoordinator], NumberEntity):
    """Representation of an RDZ HMI time setting number entity."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        setting_key: str,
        setting_name: str,
        min_value: int,
        max_value: int,
    ) -> None:
        """Initialize the time setting number entity.

        Args:
            coordinator: The data coordinator.
            setting_key: The key in the time settings dict (day, month, year, hour, minute).
            setting_name: The display name for the entity.
            min_value: The minimum allowed value.
            max_value: The maximum allowed value.
        """
        super().__init__(coordinator)
        self._setting_key = setting_key

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_time_{setting_key}"
        self._attr_translation_key = f"time_{setting_key}"
        self._attr_name = setting_name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = 1

        # Place on the System device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.client.host}_system")},
            name="RDZ HMI System",
            manufacturer="RDZ",
            model="HMI Control System",
            sw_version="1.0",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        time_settings = self.coordinator.data.get(DATA_TIME_SETTINGS, {})
        if time_settings is None:
            return None
        return time_settings.get(self._setting_key)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        int_value = int(value)

        # Call the appropriate setter method on the coordinator
        setter_methods = {
            "day": self.coordinator.async_set_time_day,
            "month": self.coordinator.async_set_time_month,
            "year": self.coordinator.async_set_time_year,
            "hour": self.coordinator.async_set_time_hour,
            "minute": self.coordinator.async_set_time_minute,
        }

        setter = setter_methods.get(self._setting_key)
        if setter is None:
            _LOGGER.error("Unknown time setting key: %s", self._setting_key)
            return

        success = await setter(int_value)
        if not success:
            _LOGGER.error("Failed to set time %s to %d", self._setting_key, int_value)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
