"""Switch platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_SEASON,
    DATA_SYSTEM_ACTIVATION,
    DOMAIN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI switch entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SwitchEntity] = [
        RDZSeasonSwitch(coordinator),
    ]

    # Add system activation switches (1-8)
    for system_id in range(1, 9):
        entities.append(RDZSystemActivationSwitch(coordinator, system_id))

    async_add_entities(entities)


class RDZSeasonSwitch(CoordinatorEntity[RDZDataUpdateCoordinator], SwitchEntity):
    """Representation of the RDZ HMI season switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "season"
    _attr_icon = "mdi:sun-snowflake-variant"

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_season_switch"

        # Create a "System" device for system-level entities
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.client.host}_system")},
            name="RDZ HMI System",
            manufacturer="RDZ",
            model="HMI Control System",
            sw_version="1.0",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if summer mode, False if winter mode."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(DATA_SEASON)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        is_summer = self.is_on
        if is_summer is None:
            season_name = "Unknown"
        elif is_summer:
            season_name = "Summer"
        else:
            season_name = "Winter"
        return {"season": season_name}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on summer mode."""
        success = await self.coordinator.async_set_season(True)
        if not success:
            _LOGGER.error("Failed to set season to summer")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn on winter mode."""
        success = await self.coordinator.async_set_season(False)
        if not success:
            _LOGGER.error("Failed to set season to winter")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class RDZSystemActivationSwitch(CoordinatorEntity[RDZDataUpdateCoordinator], SwitchEntity):
    """Representation of an RDZ HMI system activation switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        system_id: int,
    ) -> None:
        """Initialize the system activation switch entity.

        Args:
            coordinator: The data coordinator.
            system_id: The system ID (1-8).
        """
        super().__init__(coordinator)
        self._system_id = system_id

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_system_{system_id}"
        self._attr_translation_key = f"system_{system_id}"
        self._attr_name = f"System {system_id}"
        self._attr_icon = "mdi:power"

        # Place on the System device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.client.host}_system")},
            name="RDZ HMI System",
            manufacturer="RDZ",
            model="HMI Control System",
            sw_version="1.0",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the system is active."""
        if self.coordinator.data is None:
            return None
        activation = self.coordinator.data.get(DATA_SYSTEM_ACTIVATION, {})
        return activation.get(self._system_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the system."""
        success = await self.coordinator.async_set_system_activation(self._system_id, True)
        if not success:
            _LOGGER.error("Failed to activate system %d", self._system_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the system."""
        success = await self.coordinator.async_set_system_activation(self._system_id, False)
        if not success:
            _LOGGER.error("Failed to deactivate system %d", self._system_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()