"""Binary sensor platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_PUMP_ACTIVE,
    DOMAIN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI binary sensor entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Add pump active binary sensors (1-8)
    for pump_id in range(1, 9):
        entities.append(RDZPumpActiveBinarySensor(coordinator, pump_id))

    async_add_entities(entities)


class RDZPumpActiveBinarySensor(CoordinatorEntity[RDZDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an RDZ HMI pump active binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        pump_id: int,
    ) -> None:
        """Initialize the pump active binary sensor entity.

        Args:
            coordinator: The data coordinator.
            pump_id: The pump ID (1-8).
        """
        super().__init__(coordinator)
        self._pump_id = pump_id

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_pump_{pump_id}_active"
        self._attr_translation_key = f"pump_{pump_id}_active"
        self._attr_name = f"Pump {pump_id} active"

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
        """Return True if the pump is active."""
        if self.coordinator.data is None:
            return None
        pump_active = self.coordinator.data.get(DATA_PUMP_ACTIVE, {})
        return pump_active.get(self._pump_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
