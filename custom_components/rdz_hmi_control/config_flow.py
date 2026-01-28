"""Config flow for RDZ HMI Control integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_HOST,
    CONF_LINKED_VIRTUAL_ZONE,
    CONF_PORT,
    CONF_ZONE_ID,
    CONF_ZONE_NAME,
    CONF_ZONE_TYPE,
    CONF_ZONES,
    DEFAULT_PORT,
    DOMAIN,
    THERMOSTAT_TYPE_REAL,
    THERMOSTAT_TYPE_UNCONFIGURED,
    THERMOSTAT_TYPE_VIRTUAL,
)
from .modbus_client import RDZModbusClient

_LOGGER = logging.getLogger(__name__)


def _format_zone_id(zone_id: int | str) -> str:
    """Format zone ID as zero-padded two-digit string for consistent ordering."""
    return f"{int(zone_id):02d}"


class RDZHMIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RDZ HMI Control."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._discovered_zones: list[int] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - get host and port."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Validate connection
            client = RDZModbusClient(self._host, self._port)
            try:
                if await client.test_connection():
                    # Discover zones
                    self._discovered_zones = await client.discover_zones()
                    await client.disconnect()

                    if not self._discovered_zones:
                        errors["base"] = "no_zones_found"
                    else:
                        # Create unique ID based on host
                        await self.async_set_unique_id(f"rdz_hmi_{self._host}_{self._port}")
                        self._abort_if_unique_id_configured()

                        # Build initial zone config (all unconfigured)
                        # Use zero-padded string keys for consistent ordering
                        zones_config = {
                            _format_zone_id(zone_id): {
                                CONF_ZONE_ID: zone_id,
                                CONF_ZONE_NAME: f"Zone {zone_id}",
                                CONF_ZONE_TYPE: THERMOSTAT_TYPE_UNCONFIGURED,
                                CONF_LINKED_VIRTUAL_ZONE: None,
                            }
                            for zone_id in self._discovered_zones
                        }

                        return self.async_create_entry(
                            title=f"RDZ HMI ({self._host})",
                            data={
                                CONF_HOST: self._host,
                                CONF_PORT: self._port,
                                CONF_ZONES: zones_config,
                            },
                        )
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during connection test")
                errors["base"] = "unknown"
            finally:
                await client.disconnect()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RDZHMIOptionsFlow:
        """Get the options flow for this handler."""
        return RDZHMIOptionsFlow(config_entry)


class RDZHMIOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for RDZ HMI Control."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._selected_zone_id: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial options step - select zone to configure."""
        zones_config: dict = self._config_entry.data.get(CONF_ZONES, {})
        # Normalize keys to zero-padded strings for consistent ordering
        zones_config = {_format_zone_id(k): v for k, v in zones_config.items()}

        if not zones_config:
            return self.async_abort(reason="no_zones")

        if user_input is not None:
            self._selected_zone_id = int(user_input[CONF_ZONE_ID])
            return await self.async_step_configure_zone()

        # Build zone selection options
        zone_options = []
        for zone_id_str, zone_data in zones_config.items():
            zone_id = int(zone_id_str) if isinstance(zone_id_str, str) else zone_id_str
            zone_name = f"[Zone {zone_id}] "+zone_data.get(CONF_ZONE_NAME, "")
            zone_type = zone_data.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)
            type_label = {
                THERMOSTAT_TYPE_REAL: "Real",
                THERMOSTAT_TYPE_VIRTUAL: "Virtual",
                THERMOSTAT_TYPE_UNCONFIGURED: "Unconfigured",
            }.get(zone_type, "Unknown")
            zone_options.append(
                selector.SelectOptionDict(
                    value=_format_zone_id(zone_id),
                    label=f"{zone_name} ({type_label})",
                )
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=zone_options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_configure_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zone configuration step."""
        zones_config: dict = dict(self._config_entry.data.get(CONF_ZONES, {}))
        # Normalize keys to zero-padded strings for consistent ordering
        zones_config = {_format_zone_id(k): v for k, v in zones_config.items()}
        zone_id_str = _format_zone_id(self._selected_zone_id)
        current_zone = zones_config.get(zone_id_str, {})

        if user_input is not None:
            # Update zone configuration
            new_zone_config = {
                CONF_ZONE_ID: self._selected_zone_id,
                CONF_ZONE_NAME: user_input[CONF_ZONE_NAME],
                CONF_ZONE_TYPE: user_input[CONF_ZONE_TYPE],
                CONF_LINKED_VIRTUAL_ZONE: None,
            }

            # Handle linked virtual zone (only for real thermostats)
            if user_input[CONF_ZONE_TYPE] == THERMOSTAT_TYPE_REAL:
                linked = user_input.get(CONF_LINKED_VIRTUAL_ZONE)
                if linked and linked != "none":
                    new_zone_config[CONF_LINKED_VIRTUAL_ZONE] = int(linked)

            zones_config[zone_id_str] = new_zone_config

            # Update config entry data
            new_data = dict(self._config_entry.data)
            new_data[CONF_ZONES] = zones_config

            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=new_data,
            )

            return self.async_create_entry(title="", data={})

        current_name = current_zone.get(CONF_ZONE_NAME, f"Zone {self._selected_zone_id}")
        current_type = current_zone.get(CONF_ZONE_TYPE, THERMOSTAT_TYPE_UNCONFIGURED)
        current_linked = current_zone.get(CONF_LINKED_VIRTUAL_ZONE)

        # Collect virtual zones already linked to other real thermostats
        already_linked_virtuals = set()
        for zid_str, zone_data in zones_config.items():
            zid = int(zid_str) if isinstance(zid_str, str) else zid_str
            if zid != self._selected_zone_id and zone_data.get(CONF_ZONE_TYPE) == THERMOSTAT_TYPE_REAL:
                linked = zone_data.get(CONF_LINKED_VIRTUAL_ZONE)
                if linked is not None:
                    already_linked_virtuals.add(linked)

        # Build virtual zone options for linking (exclude current zone and already-linked virtuals)
        virtual_zone_options = [
            selector.SelectOptionDict(value="none", label="None")
        ]
        for zid_str, zone_data in zones_config.items():
            zid = int(zid_str) if isinstance(zid_str, str) else zid_str
            if zid != self._selected_zone_id and zone_data.get(CONF_ZONE_TYPE) == THERMOSTAT_TYPE_VIRTUAL:
                # Skip if already linked to another real thermostat
                if zid in already_linked_virtuals:
                    continue
                zone_name = zone_data.get(CONF_ZONE_NAME, f"Zone {zid}")
                virtual_zone_options.append(
                    selector.SelectOptionDict(value=_format_zone_id(zid), label=zone_name)
                )

        # Build schema
        schema_dict = {
            vol.Required(CONF_ZONE_NAME, default=current_name): str,
            vol.Required(CONF_ZONE_TYPE, default=current_type): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=THERMOSTAT_TYPE_UNCONFIGURED, label="Unconfigured"
                        ),
                        selector.SelectOptionDict(
                            value=THERMOSTAT_TYPE_REAL, label="Real"
                        ),
                        selector.SelectOptionDict(
                            value=THERMOSTAT_TYPE_VIRTUAL, label="Virtual"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # Show linked virtual zone option when virtual zones are available
        # (selection is only used if user chooses "Real" type - handled in user_input processing)
        if len(virtual_zone_options) > 1:
            schema_dict[vol.Optional(
                CONF_LINKED_VIRTUAL_ZONE,
                default=_format_zone_id(current_linked) if current_linked else "none"
            )] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=virtual_zone_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(
            step_id="configure_zone",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "zone_name": current_name,
            },
        )
