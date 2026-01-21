"""Data coordinator for RDZ HMI Control integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_LINKED_VIRTUAL_ZONE,
    CONF_PORT,
    CONF_ZONE_TYPE,
    CONF_ZONES,
    DATA_SEASON,
    DATA_SUMMER_SETPOINTS,
    DATA_TEMPERATURES,
    DATA_WINTER_SETPOINTS,
    DATA_ZONE_ACTIVITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    THERMOSTAT_TYPE_REAL,
)
from .modbus_client import RDZModbusClient

_LOGGER = logging.getLogger(__name__)


class RDZDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching RDZ HMI data from Modbus."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self._host = config_entry.data[CONF_HOST]
        self._port = config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        self.client = RDZModbusClient(self._host, self._port)
        self._previous_winter_setpoints: dict[int, float] = {}
        self._previous_summer_setpoints: dict[int, float] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    @property
    def zones_config(self) -> dict[str, dict]:
        """Get current zones configuration."""
        return self.config_entry.data.get(CONF_ZONES, {})

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Modbus device."""
        try:
            # Read all data in parallel would be nice, but we need to serialize
            # to avoid issues with the Modbus connection
            temperatures = await self.client.read_temperatures()
            winter_setpoints = await self.client.read_winter_setpoints()
            summer_setpoints = await self.client.read_summer_setpoints()
            season = await self.client.read_season()
            zone_activity = await self.client.read_zone_activity()

            if temperatures is None or winter_setpoints is None or summer_setpoints is None:
                raise UpdateFailed("Failed to read data from Modbus device")

            # Check for setpoint changes and sync from real to linked virtual thermostats
            await self._sync_linked_setpoints(winter_setpoints, summer_setpoints)

            self._previous_winter_setpoints = dict(winter_setpoints)
            self._previous_summer_setpoints = dict(summer_setpoints)

            return {
                DATA_TEMPERATURES: temperatures,
                DATA_WINTER_SETPOINTS: winter_setpoints,
                DATA_SUMMER_SETPOINTS: summer_setpoints,
                DATA_SEASON: season,  # True = summer, False = winter, None = unknown
                DATA_ZONE_ACTIVITY: zone_activity,  # dict of zone_id -> is_active
            }

        except Exception as ex:
            raise UpdateFailed(f"Error communicating with Modbus device: {ex}") from ex

    async def async_set_season(self, is_summer: bool) -> bool:
        """Set the season (True = summer, False = winter)."""
        success = await self.client.write_season(is_summer)
        if success:
            await self.async_request_refresh()
        return success

    async def _sync_linked_setpoints(
        self,
        current_winter_setpoints: dict[int, float],
        current_summer_setpoints: dict[int, float],
    ) -> None:
        """Sync setpoint changes from real thermostats to linked virtual thermostats."""
        zones_config = self.zones_config

        # Find all real thermostats with linked virtual thermostats
        for zone_id_str, zone_data in zones_config.items():
            real_zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str

            if zone_data.get(CONF_ZONE_TYPE) != THERMOSTAT_TYPE_REAL:
                continue

            virtual_zone_id = zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
            if virtual_zone_id is None:
                continue

            # Check if the real thermostat's winter setpoint changed
            prev_winter = self._previous_winter_setpoints.get(real_zone_id)
            curr_winter = current_winter_setpoints.get(real_zone_id)

            if prev_winter is not None and curr_winter is not None and prev_winter != curr_winter:
                _LOGGER.info(
                    "Real zone %d winter setpoint changed from %.1f to %.1f, "
                    "syncing to virtual zone %d",
                    real_zone_id,
                    prev_winter,
                    curr_winter,
                    virtual_zone_id,
                )
                success = await self.client.write_winter_setpoint(virtual_zone_id, curr_winter)
                if not success:
                    _LOGGER.error(
                        "Failed to sync winter setpoint to virtual zone %d",
                        virtual_zone_id,
                    )

            # Check if the real thermostat's summer setpoint changed
            prev_summer = self._previous_summer_setpoints.get(real_zone_id)
            curr_summer = current_summer_setpoints.get(real_zone_id)

            if prev_summer is not None and curr_summer is not None and prev_summer != curr_summer:
                _LOGGER.info(
                    "Real zone %d summer setpoint changed from %.1f to %.1f, "
                    "syncing to virtual zone %d",
                    real_zone_id,
                    prev_summer,
                    curr_summer,
                    virtual_zone_id,
                )
                success = await self.client.write_summer_setpoint(virtual_zone_id, curr_summer)
                if not success:
                    _LOGGER.error(
                        "Failed to sync summer setpoint to virtual zone %d",
                        virtual_zone_id,
                    )

    async def async_set_temperature(
        self, zone_id: int, temperature: float, hvac_mode: HVACMode
    ) -> bool:
        """Set the temperature for a zone based on current HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            success = await self.client.write_winter_setpoint(zone_id, temperature)
        elif hvac_mode == HVACMode.COOL:
            success = await self.client.write_summer_setpoint(zone_id, temperature)
        else:
            _LOGGER.warning(
                "Cannot set temperature for zone %d in %s mode", zone_id, hvac_mode
            )
            return False

        if success:
            # Request a data refresh to update the UI
            await self.async_request_refresh()

        return success

    async def async_shutdown(self) -> None:
        """Disconnect from the Modbus device."""
        await self.client.disconnect()
