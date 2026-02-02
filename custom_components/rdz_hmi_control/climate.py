"""Climate platform for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_LINKED_VIRTUAL_ZONE,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONES,
    DATA_CALCULATED_SETPOINTS,
    DATA_SEASON,
    DATA_SUMMER_SETPOINTS,
    DATA_TEMPERATURES,
    DATA_WINTER_SETPOINTS,
    DATA_ZONE_ACTIVITY,
    DATA_ZONE_MODES,
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
    TEMP_STEP,
    THERMOSTAT_TYPE_REAL,
    THERMOSTAT_TYPE_UNCONFIGURED,
    THERMOSTAT_TYPE_VIRTUAL,
    ZONE_MODE_MAN,
    ZONE_MODE_OFF,
    ZONE_MODE_OPTIONS,
    ZONE_MODE_PGM,
    ZONE_MODE_PGM_MAN,
)
from .coordinator import RDZDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Preset modes that map to zone modes
PRESET_OFF = "Off"
PRESET_MAN = "Man"
PRESET_PGM = "Pgm"
PRESET_PGM_MAN = "Pgm/Man"

PRESET_MODE_TO_ZONE_MODE = {
    PRESET_OFF: ZONE_MODE_OFF,
    PRESET_MAN: ZONE_MODE_MAN,
    PRESET_PGM: ZONE_MODE_PGM,
    PRESET_PGM_MAN: ZONE_MODE_PGM_MAN,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RDZ HMI climate entities from a config entry."""
    coordinator: RDZDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones_config = config_entry.data.get(CONF_ZONES, {})

    entities = []
    for zone_id_str, zone_data in zones_config.items():
        zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
        entities.append(RDZClimateEntity(coordinator, zone_id, zone_data))

    async_add_entities(entities)


class RDZClimateEntity(CoordinatorEntity[RDZDataUpdateCoordinator], ClimateEntity):
    """Representation of an RDZ HMI thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _attr_preset_modes = [PRESET_OFF, PRESET_MAN, PRESET_PGM, PRESET_PGM_MAN]
    _enable_turn_on_off_backwards_compat = False

    def __init__(
        self,
        coordinator: RDZDataUpdateCoordinator,
        zone_id: int,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone_data = zone_data
        self._attr_unique_id = f"{DOMAIN}_{coordinator.client.host}_{zone_id}_climate"

        self._update_from_zone_data()

    def _update_from_zone_data(self) -> None:
        """Update entity attributes from zone data."""
        zones_config = self.coordinator.config_entry.data.get(CONF_ZONES, {})
        zone_data = zones_config.get(str(self._zone_id), self._zone_data)
        self._zone_data = zone_data

        zone_name = zone_data.get(CONF_ZONE_NAME, f"Zone {self._zone_id}")
        zone_type = zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)

        # Set supported features and HVAC modes based on configuration
        if zone_type == THERMOSTAT_TYPE_UNCONFIGURED:
            self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
            self._attr_hvac_modes = [HVACMode.OFF]
        elif zone_type == THERMOSTAT_TYPE_VIRTUAL:
            # Virtual thermostats are read-only (synced from real thermostats)
            self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
            self._attr_hvac_modes = [HVACMode.OFF]
        else:  # THERMOSTAT_TYPE_REAL
            # Real thermostats support temperature control and preset mode
            # HVAC mode is determined by season switch (read-only)
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.PRESET_MODE
            )
            self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL]

        # Update device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.client.host}_{self._zone_id}")},
            name=zone_name,
            manufacturer="RDZ",
            model="HMI Thermostat",
            sw_version="1.0",
        )

    def _get_season_based_hvac_mode(self) -> HVACMode:
        """Get HVAC mode based on season switch (summer=COOL, winter=HEAT)."""
        if self.coordinator.data is None:
            return HVACMode.HEAT  # Default to heat if no data

        season = self.coordinator.data.get(DATA_SEASON)
        if season is True:  # Summer
            return HVACMode.COOL
        else:  # Winter or unknown
            return HVACMode.HEAT

    def _get_effective_zone_id_for_preset(self) -> int:
        """Get the zone ID to use for preset operations based on season.

        For real thermostats with linked virtual zone:
        - Summer mode: use linked virtual zone ID (presets control cooling)
        - Winter mode: use this zone ID (presets control heating)

        For all other thermostats: use own zone ID.
        """
        zone_type = self._zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)

        if zone_type == THERMOSTAT_TYPE_REAL:
            linked_virtual = self._zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
            if linked_virtual is not None:
                current_mode = self._get_season_based_hvac_mode()
                if current_mode == HVACMode.COOL:  # Summer
                    return linked_virtual

        return self._zone_id

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self.coordinator.data is None:
            return None
        temperatures = self.coordinator.data.get(DATA_TEMPERATURES, {})
        return temperatures.get(self._zone_id)

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature based on zone mode and season.

        In 'Man' mode: return manual setpoint (winter or summer based on season)
        In other modes: return calculated setpoint from program
        """
        if self.coordinator.data is None:
            return None

        effective_zone_id = self._get_effective_zone_id_for_preset()
        zone_modes = self.coordinator.data.get(DATA_ZONE_MODES, {})
        current_zone_mode = zone_modes.get(effective_zone_id)

        # Only use manual setpoints in Man mode
        if current_zone_mode == ZONE_MODE_MAN:
            current_hvac_mode = self._get_season_based_hvac_mode()
            if current_hvac_mode == HVACMode.COOL:
                setpoints = self.coordinator.data.get(DATA_SUMMER_SETPOINTS, {})
            else:
                setpoints = self.coordinator.data.get(DATA_WINTER_SETPOINTS, {})
            return setpoints.get(self._zone_id)

        # All other modes: use calculated setpoints from effective zone
        calculated = self.coordinator.data.get(DATA_CALCULATED_SETPOINTS, {})
        return calculated.get(effective_zone_id)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode based on season switch (read-only)."""
        zone_type = self._zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)

        if zone_type in (THERMOSTAT_TYPE_UNCONFIGURED, THERMOSTAT_TYPE_VIRTUAL):
            return HVACMode.OFF

        return self._get_season_based_hvac_mode()

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action based on zone activity bitmasks.

        For real thermostats:
        - HEATING: This zone's bit is set in the activity bitmask
        - COOLING: Linked virtual zone's bit is set in the activity bitmask
        - IDLE: Neither this zone nor linked virtual zone is active
        """
        zone_type = self._zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)

        if zone_type in (THERMOSTAT_TYPE_UNCONFIGURED, THERMOSTAT_TYPE_VIRTUAL):
            return HVACAction.OFF

        if self.coordinator.data is None:
            return HVACAction.IDLE

        zone_activity = self.coordinator.data.get(DATA_ZONE_ACTIVITY, {})

        # Check if this zone is actively heating
        if zone_activity.get(self._zone_id, False):
            return HVACAction.HEATING

        # Check if linked virtual zone is active (cooling)
        linked_virtual = self._zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
        if linked_virtual is not None and zone_activity.get(linked_virtual, False):
            return HVACAction.COOLING

        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode based on zone mode."""
        if self.coordinator.data is None:
            return None

        effective_zone_id = self._get_effective_zone_id_for_preset()
        zone_modes = self.coordinator.data.get(DATA_ZONE_MODES, {})
        mode_value = zone_modes.get(effective_zone_id)

        if mode_value is None:
            return None

        return ZONE_MODE_OPTIONS.get(mode_value, ZONE_MODE_OPTIONS[ZONE_MODE_OFF])

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode by writing to the appropriate zone mode register."""
        mode_value = PRESET_MODE_TO_ZONE_MODE.get(preset_mode)
        if mode_value is None:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
            return

        effective_zone_id = self._get_effective_zone_id_for_preset()
        success = await self.coordinator.async_set_zone_mode(effective_zone_id, mode_value)
        if not success:
            _LOGGER.error("Failed to set preset for zone %d", self._zone_id)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """HVAC mode is read-only - determined by season switch."""
        _LOGGER.debug(
            "HVAC mode change requested for zone %d, but mode is determined by season switch",
            self._zone_id,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        zone_type = self._zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)

        if zone_type == THERMOSTAT_TYPE_UNCONFIGURED:
            _LOGGER.warning(
                "Cannot set temperature for unconfigured zone %d. "
                "Please configure the thermostat type in integration options.",
                self._zone_id,
            )
            return

        if zone_type == THERMOSTAT_TYPE_VIRTUAL:
            _LOGGER.warning(
                "Cannot set temperature for virtual zone %d. "
                "Virtual thermostats are synced from linked real thermostats.",
                self._zone_id,
            )
            return

        # Check if in Man mode using effective zone ID
        if self.coordinator.data:
            effective_zone_id = self._get_effective_zone_id_for_preset()
            zone_modes = self.coordinator.data.get(DATA_ZONE_MODES, {})
            if zone_modes.get(effective_zone_id) != ZONE_MODE_MAN:
                _LOGGER.warning(
                    "Cannot set temperature for zone %d - not in manual mode. "
                    "Change preset to 'Man' first.",
                    self._zone_id,
                )
                return

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        current_mode = self._get_season_based_hvac_mode()
        success = await self.coordinator.async_set_temperature(
            self._zone_id, temperature, current_mode
        )
        if not success:
            _LOGGER.error("Failed to set temperature for zone %d", self._zone_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_from_zone_data()
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
        self._update_from_zone_data()
        self.async_write_ha_state()
