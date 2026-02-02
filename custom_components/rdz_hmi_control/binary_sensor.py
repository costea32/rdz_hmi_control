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
    CONF_LINKED_VIRTUAL_ZONE,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONES,
    DATA_DEHUMIDIFICATION_PUMP,
    DATA_HUMIDITY_REQUEST,
    DATA_INTEGRATION_REQUEST,
    DATA_PUMP_ACTIVE,
    DATA_RENEWAL_REQUEST,
    DATA_VENTILATION_MODE_DEHUMIDIFICATION,
    DATA_VENTILATION_MODE_INTEGRATION,
    DATA_VENTILATION_MODE_RENEWAL,
    DATA_VENTILATION_MODE_VENTILATION,
    DATA_VENTILATION_REQUEST,
    DATA_ZONE_ACTIVITY,
    DOMAIN,
    THERMOSTAT_TYPE_REAL,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Zone request types with their data keys and display names
ZONE_REQUEST_TYPES: dict[str, tuple[str, str]] = {
    "humidity_request": (DATA_HUMIDITY_REQUEST, "Humidity request"),
    "ventilation_request": (DATA_VENTILATION_REQUEST, "Ventilation request"),
    "renewal_request": (DATA_RENEWAL_REQUEST, "Renewal request"),
    "integration_request": (DATA_INTEGRATION_REQUEST, "Integration request"),
    "dehumidification_pump": (DATA_DEHUMIDIFICATION_PUMP, "Dehumidification pump"),
}

# Ventilation mode types with their data keys and display names
VENTILATION_MODE_TYPES: dict[str, tuple[str, str]] = {
    "dehumidification": (DATA_VENTILATION_MODE_DEHUMIDIFICATION, "Dehumidification"),
    "ventilation": (DATA_VENTILATION_MODE_VENTILATION, "Ventilation"),
    "renewal": (DATA_VENTILATION_MODE_RENEWAL, "Renewal"),
    "integration": (DATA_VENTILATION_MODE_INTEGRATION, "Integration"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI binary sensor entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones_config = config_entry.data.get(CONF_ZONES, {})

    entities: list[BinarySensorEntity] = []

    # Add pump active binary sensors (1-8)
    for pump_id in range(1, 9):
        entities.append(RDZPumpActiveBinarySensor(coordinator, pump_id))

    # Add ventilation mode binary sensors
    for mode_type in VENTILATION_MODE_TYPES:
        entities.append(RDZVentilationModeBinarySensor(coordinator, mode_type))

    # Add zone pump binary sensors for each configured zone
    for zone_id_str, zone_data in zones_config.items():
        zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
        entities.append(RDZZonePumpBinarySensor(coordinator, zone_id, zone_data))

        # Add zone request binary sensors (5 per zone)
        for request_type in ZONE_REQUEST_TYPES:
            entities.append(
                RDZZoneRequestBinarySensor(coordinator, zone_id, zone_data, request_type)
            )

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


class RDZVentilationModeBinarySensor(CoordinatorEntity[RDZDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an RDZ HMI ventilation mode binary sensor.

    Indicates whether a ventilation unit work mode is active.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        mode_type: str,
    ) -> None:
        """Initialize the ventilation mode binary sensor entity.

        Args:
            coordinator: The data coordinator.
            mode_type: The type of ventilation mode (key in VENTILATION_MODE_TYPES).
        """
        super().__init__(coordinator)
        self._mode_type = mode_type
        self._data_key, self._display_name = VENTILATION_MODE_TYPES[mode_type]

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_ventilation_mode_{mode_type}"
        self._attr_name = self._display_name

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
        """Return True if the ventilation mode is active."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class RDZZonePumpBinarySensor(CoordinatorEntity[RDZDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an RDZ HMI zone pump binary sensor.

    Indicates whether the zone is actively heating or cooling.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict,
    ) -> None:
        """Initialize the zone pump binary sensor entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data

        zone_name = zone_data.get(CONF_ZONE_NAME, f"Zone {zone_id}")

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_{zone_id}_zone_pump"
        self._attr_name = "Zone pump"

        # Place on the zone's device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.client.host}_{zone_id}")},
            name=zone_name,
            manufacturer="RDZ",
            model="HMI Thermostat",
            sw_version="1.0",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the zone is actively heating or cooling.

        Uses the same logic as hvac_action in climate.py:
        - For real thermostats: True if this zone or linked virtual zone is active
        - For virtual/unconfigured: Always False
        """
        zone_type = self._zone_data.get(CONF_ZONE_TYPE)

        if zone_type != THERMOSTAT_TYPE_REAL:
            return False

        if self.coordinator.data is None:
            return None

        zone_activity = self.coordinator.data.get(DATA_ZONE_ACTIVITY, {})

        # Check if this zone is active
        if zone_activity.get(self._zone_id, False):
            return True

        # Check if linked virtual zone is active
        linked_virtual = self._zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
        if linked_virtual is not None and zone_activity.get(linked_virtual, False):
            return True

        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update zone_data in case config changed
        zones_config = self.coordinator.config_entry.data.get(CONF_ZONES, {})
        self._zone_data = zones_config.get(str(self._zone_id), self._zone_data)
        self.async_write_ha_state()


class RDZZoneRequestBinarySensor(CoordinatorEntity[RDZDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an RDZ HMI zone request binary sensor.

    Indicates whether the zone has an active request (humidity, ventilation,
    renewal, integration, or dehumidification pump).
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict,
        request_type: str,
    ) -> None:
        """Initialize the zone request binary sensor entity.

        Args:
            coordinator: The data coordinator.
            zone_id: The zone ID (0-63).
            zone_data: Zone configuration data.
            request_type: The type of request (key in ZONE_REQUEST_TYPES).
        """
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data
        self._request_type = request_type
        self._data_key, self._display_name = ZONE_REQUEST_TYPES[request_type]

        zone_name = zone_data.get(CONF_ZONE_NAME, f"Zone {zone_id}")

        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_{zone_id}_{request_type}"
        self._attr_name = self._display_name

        # Place on the zone's device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.client.host}_{zone_id}")},
            name=zone_name,
            manufacturer="RDZ",
            model="HMI Thermostat",
            sw_version="1.0",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the zone has the request active.

        Uses the same logic as RDZZonePumpBinarySensor:
        - For real thermostats: True if this zone or linked virtual zone is active
        - For virtual/unconfigured: Always False
        """
        zone_type = self._zone_data.get(CONF_ZONE_TYPE)

        if zone_type != THERMOSTAT_TYPE_REAL:
            return False

        if self.coordinator.data is None:
            return None

        request_data = self.coordinator.data.get(self._data_key, {})

        # Check if this zone has the request active
        if request_data.get(self._zone_id, False):
            return True

        # Check if linked virtual zone has the request active
        linked_virtual = self._zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
        if linked_virtual is not None and request_data.get(linked_virtual, False):
            return True

        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update zone_data in case config changed
        zones_config = self.coordinator.config_entry.data.get(CONF_ZONES, {})
        self._zone_data = zones_config.get(str(self._zone_id), self._zone_data)
        self.async_write_ha_state()
