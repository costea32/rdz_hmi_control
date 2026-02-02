"""Async Modbus TCP client wrapper for RDZ HMI Control."""

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    COIL_SEASON,
    COIL_SYSTEM_ACTIVATION_START,
    COIL_SYSTEM_ACTIVATION_COUNT,
    REGISTER_ACTIVITY_COUNT,
    REGISTER_ACTIVITY_START,
    REGISTER_CALCULATED_SETPOINT_COUNT,
    REGISTER_CALCULATED_SETPOINT_START,
    REGISTER_CALCULATED_WATER_TEMP_COUNT,
    REGISTER_CALCULATED_WATER_TEMP_START,
    REGISTER_DEHUMIDIFICATION_PUMP_COUNT,
    REGISTER_DEHUMIDIFICATION_PUMP_START,
    REGISTER_DEHUMIDIFICATION_SETPOINT_COUNT,
    REGISTER_DEHUMIDIFICATION_SETPOINT_START,
    REGISTER_DELIVERY_WATER_TEMP_COUNT,
    REGISTER_DELIVERY_WATER_TEMP_START,
    REGISTER_DEW_POINT_COUNT,
    REGISTER_DEW_POINT_START,
    REGISTER_HUMIDITY_COUNT,
    REGISTER_HUMIDITY_REQUEST_COUNT,
    REGISTER_HUMIDITY_REQUEST_START,
    REGISTER_HUMIDITY_START,
    REGISTER_INTEGRATION_REQUEST_COUNT,
    REGISTER_INTEGRATION_REQUEST_START,
    REGISTER_OUTSIDE_TEMP,
    REGISTER_PUMP_ACTIVE,
    REGISTER_RENEWAL_REQUEST_COUNT,
    REGISTER_RENEWAL_REQUEST_START,
    REGISTER_TEMP_START,
    REGISTER_TEMP_COUNT,
    REGISTER_TIME_DAY,
    REGISTER_TIME_HOUR,
    REGISTER_TIME_MINUTE,
    REGISTER_TIME_MONTH,
    REGISTER_TIME_YEAR,
    REGISTER_VENTILATION_REQUEST_COUNT,
    REGISTER_VENTILATION_REQUEST_START,
    REGISTER_WINTER_SETPOINT_START,
    REGISTER_WINTER_SETPOINT_COUNT,
    REGISTER_SUMMER_SETPOINT_START,
    REGISTER_SUMMER_SETPOINT_COUNT,
    REGISTER_ZONE_MODE_COUNT,
    REGISTER_ZONE_MODE_START,
    TEMP_SCALE_FACTOR,
)

_LOGGER = logging.getLogger(__name__)


class RDZModbusClient:
    """Async Modbus TCP client for RDZ HMI thermostats."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the Modbus client."""
        self._host = host
        self._port = port
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the port."""
        return self._port

    async def _connect_unlocked(self) -> bool:
        """Connect to the Modbus device (must be called with lock held)."""
        if self._client is not None and self._client.connected:
            return True

        self._client = AsyncModbusTcpClient(
            host=self._host,
            port=self._port,
            timeout=10,  # 10 second timeout
        )

        try:
            connected = await self._client.connect()
            if connected:
                _LOGGER.debug("Connected to Modbus device at %s:%s", self._host, self._port)
            else:
                _LOGGER.error("Failed to connect to Modbus device at %s:%s", self._host, self._port)
            return connected
        except Exception as ex:
            _LOGGER.error("Error connecting to Modbus device: %s", ex)
            return False

    async def connect(self) -> bool:
        """Connect to the Modbus device."""
        async with self._lock:
            return await self._connect_unlocked()

    async def disconnect(self) -> None:
        """Disconnect from the Modbus device."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None
                _LOGGER.debug("Disconnected from Modbus device")

    async def read_registers(self, address: int, count: int) -> list[int] | None:
        """Read holding registers from the Modbus device."""
        async with self._lock:
            if not await self._connect_unlocked():
                return None

            try:
                result = await self._client.read_holding_registers(address=address, count=count)
                if result.isError():
                    _LOGGER.error("Error reading registers at %d: %s", address, result)
                    return None
                return list(result.registers)
            except ModbusException as ex:
                _LOGGER.error("Modbus exception reading registers at %d: %s", address, ex)
                return None
            except Exception as ex:
                _LOGGER.error("Unexpected error reading registers at %d: %s", address, ex)
                return None

    async def write_register(self, address: int, value: int) -> bool:
        """Write a single holding register to the Modbus device."""
        async with self._lock:
            if not await self._connect_unlocked():
                return False

            try:
                result = await self._client.write_register(address=address, value=value)
                if result.isError():
                    _LOGGER.error("Error writing register at %d: %s", address, result)
                    return False
                _LOGGER.debug("Wrote value %d to register %d", value, address)
                return True
            except ModbusException as ex:
                _LOGGER.error("Modbus exception writing register at %d: %s", address, ex)
                return False
            except Exception as ex:
                _LOGGER.error("Unexpected error writing register at %d: %s", address, ex)
                return False

    async def read_coil(self, address: int) -> bool | None:
        """Read a single coil from the Modbus device."""
        async with self._lock:
            if not await self._connect_unlocked():
                return None

            try:
                result = await self._client.read_coils(address=address, count=1)
                if result.isError():
                    _LOGGER.error("Error reading coil at %d: %s", address, result)
                    return None
                return result.bits[0]
            except ModbusException as ex:
                _LOGGER.error("Modbus exception reading coil at %d: %s", address, ex)
                return None
            except Exception as ex:
                _LOGGER.error("Unexpected error reading coil at %d: %s", address, ex)
                return None

    async def write_coil(self, address: int, value: bool) -> bool:
        """Write a single coil to the Modbus device."""
        async with self._lock:
            if not await self._connect_unlocked():
                return False

            try:
                result = await self._client.write_coil(address=address, value=value)
                if result.isError():
                    _LOGGER.error("Error writing coil at %d: %s", address, result)
                    return False
                _LOGGER.debug("Wrote value %s to coil %d", value, address)
                return True
            except ModbusException as ex:
                _LOGGER.error("Modbus exception writing coil at %d: %s", address, ex)
                return False
            except Exception as ex:
                _LOGGER.error("Unexpected error writing coil at %d: %s", address, ex)
                return False

    async def read_season(self) -> bool | None:
        """Read the season coil. Returns True for summer, False for winter."""
        return await self.read_coil(COIL_SEASON)

    async def write_season(self, is_summer: bool) -> bool:
        """Write the season coil. True for summer, False for winter."""
        return await self.write_coil(COIL_SEASON, is_summer)

    async def read_temperatures(self) -> dict[int, float] | None:
        """Read all temperature registers and return non-zero values."""
        registers = await self.read_registers(REGISTER_TEMP_START, REGISTER_TEMP_COUNT)
        if registers is None:
            return None

        temperatures = {}
        for i, value in enumerate(registers):
            if value != 0:
                temperatures[i] = value / TEMP_SCALE_FACTOR
        return temperatures

    async def read_winter_setpoints(self) -> dict[int, float] | None:
        """Read all winter setpoint registers."""
        registers = await self.read_registers(
            REGISTER_WINTER_SETPOINT_START, REGISTER_WINTER_SETPOINT_COUNT
        )
        if registers is None:
            return None

        return {i: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_summer_setpoints(self) -> dict[int, float] | None:
        """Read all summer setpoint registers."""
        registers = await self.read_registers(
            REGISTER_SUMMER_SETPOINT_START, REGISTER_SUMMER_SETPOINT_COUNT
        )
        if registers is None:
            return None

        return {i: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_calculated_setpoints(self) -> dict[int, float] | None:
        """Read all calculated setpoint registers.

        These are program-calculated target temperatures used in non-manual modes.
        Values are stored as integer * 10 (e.g., 21.5°C = 215).
        """
        registers = await self.read_registers(
            REGISTER_CALCULATED_SETPOINT_START, REGISTER_CALCULATED_SETPOINT_COUNT
        )
        if registers is None:
            return None

        return {i: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_zone_activity(self) -> dict[int, bool] | None:
        """Read zone activity bitmasks and return dict of zone_id -> is_active.

        Registers 2892-2895 contain 16-bit bitmasks indicating active zones:
        - Register 2892: Zones 0-15 (bit 0 = zone 0)
        - Register 2893: Zones 16-31 (bit 0 = zone 16)
        - Register 2894: Zones 32-47 (bit 0 = zone 32)
        - Register 2895: Zones 48-63 (bit 0 = zone 48)

        Bit = 1 means zone is actively heating/cooling, bit = 0 means idle.
        """
        registers = await self.read_registers(
            REGISTER_ACTIVITY_START, REGISTER_ACTIVITY_COUNT
        )
        if registers is None:
            return None

        activity: dict[int, bool] = {}
        for reg_idx, reg_value in enumerate(registers):
            for bit in range(16):
                zone_id = reg_idx * 16 + bit
                activity[zone_id] = bool(reg_value & (1 << bit))
        return activity

    async def write_winter_setpoint(self, zone_id: int, temperature: float) -> bool:
        """Write a winter setpoint for a zone."""
        address = REGISTER_WINTER_SETPOINT_START + zone_id
        value = int(temperature * TEMP_SCALE_FACTOR)
        return await self.write_register(address, value)

    async def write_summer_setpoint(self, zone_id: int, temperature: float) -> bool:
        """Write a summer setpoint for a zone."""
        address = REGISTER_SUMMER_SETPOINT_START + zone_id
        value = int(temperature * TEMP_SCALE_FACTOR)
        return await self.write_register(address, value)

    async def read_humidity(self) -> dict[int, float] | None:
        """Read all humidity registers and return dict of zone_id -> humidity %.

        Values are stored as integer * 10 (e.g., 55.0% = 550).
        """
        registers = await self.read_registers(
            REGISTER_HUMIDITY_START, REGISTER_HUMIDITY_COUNT
        )
        if registers is None:
            return None

        return {i: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_dehumidification_setpoints(self) -> dict[int, int] | None:
        """Read all dehumidification setpoint registers.

        Values are stored as raw percentage (e.g., 50% = 50).
        """
        registers = await self.read_registers(
            REGISTER_DEHUMIDIFICATION_SETPOINT_START,
            REGISTER_DEHUMIDIFICATION_SETPOINT_COUNT,
        )
        if registers is None:
            return None

        return {i: value for i, value in enumerate(registers)}

    async def write_dehumidification_setpoint(
        self, zone_id: int, humidity: int
    ) -> bool:
        """Write a dehumidification setpoint for a zone.

        Args:
            zone_id: The zone ID (0-63).
            humidity: The target humidity percentage (e.g., 50).
        """
        address = REGISTER_DEHUMIDIFICATION_SETPOINT_START + zone_id
        return await self.write_register(address, humidity)

    async def read_dew_points(self) -> dict[int, float] | None:
        """Read all dew point registers.

        Values are stored as integer * 10 (e.g., 15.5°C = 155).
        """
        registers = await self.read_registers(
            REGISTER_DEW_POINT_START, REGISTER_DEW_POINT_COUNT
        )
        if registers is None:
            return None

        return {i: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_zone_modes(self) -> dict[int, int] | None:
        """Read all zone mode registers.

        Returns dict of zone_id -> mode (0=Off, 1=Man, 2=Pgm, 3=Pgm/Man).
        """
        registers = await self.read_registers(
            REGISTER_ZONE_MODE_START, REGISTER_ZONE_MODE_COUNT
        )
        if registers is None:
            return None

        return {i: value for i, value in enumerate(registers)}

    async def write_zone_mode(self, zone_id: int, mode: int) -> bool:
        """Write a zone mode.

        Args:
            zone_id: The zone ID (0-63).
            mode: The mode value (0=Off, 1=Man, 2=Pgm, 3=Pgm/Man).
        """
        address = REGISTER_ZONE_MODE_START + zone_id
        return await self.write_register(address, mode)

    async def discover_zones(self) -> list[int]:
        """Discover active zones by reading temperature registers."""
        temperatures = await self.read_temperatures()
        if temperatures is None:
            return []
        return list(temperatures.keys())

    async def test_connection(self) -> bool:
        """Test the connection to the Modbus device."""
        if not await self.connect():
            return False

        # Try reading temperature registers as a connection test
        result = await self.read_registers(REGISTER_TEMP_START, 1)
        return result is not None

    async def read_outside_temperature(self) -> float | None:
        """Read the outside temperature from register 2600.

        Value is stored as integer * 10 (e.g., 21.5°C = 215).
        """
        registers = await self.read_registers(REGISTER_OUTSIDE_TEMP, 1)
        if registers is None:
            return None
        return registers[0] / TEMP_SCALE_FACTOR

    async def read_time_settings(self) -> dict[str, int] | None:
        """Read time settings from registers 5009-5013.

        Returns dict with keys: day, month, year, hour, minute
        """
        registers = await self.read_registers(REGISTER_TIME_DAY, 5)
        if registers is None:
            return None
        return {
            "day": registers[0],
            "month": registers[1],
            "year": registers[2],
            "hour": registers[3],
            "minute": registers[4],
        }

    async def write_time_day(self, day: int) -> bool:
        """Write the day value to register 5009."""
        return await self.write_register(REGISTER_TIME_DAY, day)

    async def write_time_month(self, month: int) -> bool:
        """Write the month value to register 5010."""
        return await self.write_register(REGISTER_TIME_MONTH, month)

    async def write_time_year(self, year: int) -> bool:
        """Write the year value to register 5011."""
        return await self.write_register(REGISTER_TIME_YEAR, year)

    async def write_time_hour(self, hour: int) -> bool:
        """Write the hour value to register 5012."""
        return await self.write_register(REGISTER_TIME_HOUR, hour)

    async def write_time_minute(self, minute: int) -> bool:
        """Write the minute value to register 5013."""
        return await self.write_register(REGISTER_TIME_MINUTE, minute)

    async def read_coils(self, address: int, count: int) -> list[bool] | None:
        """Read multiple coils from the Modbus device."""
        async with self._lock:
            if not await self._connect_unlocked():
                return None

            try:
                result = await self._client.read_coils(address=address, count=count)
                if result.isError():
                    _LOGGER.error("Error reading coils at %d: %s", address, result)
                    return None
                return list(result.bits[:count])
            except ModbusException as ex:
                _LOGGER.error("Modbus exception reading coils at %d: %s", address, ex)
                return None
            except Exception as ex:
                _LOGGER.error("Unexpected error reading coils at %d: %s", address, ex)
                return None

    async def read_system_activation(self) -> dict[int, bool] | None:
        """Read system activation coils 100-107.

        Returns dict of system_id (1-8) -> is_on (True/False).
        """
        coils = await self.read_coils(COIL_SYSTEM_ACTIVATION_START, COIL_SYSTEM_ACTIVATION_COUNT)
        if coils is None:
            return None
        return {i + 1: coils[i] for i in range(COIL_SYSTEM_ACTIVATION_COUNT)}

    async def write_system_activation(self, system_id: int, is_on: bool) -> bool:
        """Write a system activation coil.

        Args:
            system_id: The system ID (1-8).
            is_on: Whether to activate (True) or deactivate (False).
        """
        if not 1 <= system_id <= 8:
            _LOGGER.error("Invalid system_id %d, must be 1-8", system_id)
            return False
        address = COIL_SYSTEM_ACTIVATION_START + (system_id - 1)
        return await self.write_coil(address, is_on)

    async def read_delivery_water_temps(self) -> dict[int, float] | None:
        """Read delivery water temperatures from registers 2650-2657.

        Returns dict of system_id (1-8) -> temperature.
        Values are stored as integer * 10.
        """
        registers = await self.read_registers(
            REGISTER_DELIVERY_WATER_TEMP_START, REGISTER_DELIVERY_WATER_TEMP_COUNT
        )
        if registers is None:
            return None
        return {i + 1: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_calculated_water_temps(self) -> dict[int, float] | None:
        """Read calculated water temperatures from registers 2658-2665.

        Returns dict of system_id (1-8) -> temperature.
        Values are stored as integer * 10.
        """
        registers = await self.read_registers(
            REGISTER_CALCULATED_WATER_TEMP_START, REGISTER_CALCULATED_WATER_TEMP_COUNT
        )
        if registers is None:
            return None
        return {i + 1: value / TEMP_SCALE_FACTOR for i, value in enumerate(registers)}

    async def read_pump_active(self) -> dict[int, bool] | None:
        """Read pump active status from register 7615 bitmask.

        Returns dict of pump_id (1-8) -> is_active (True/False).
        Bit 0 = pump 1, bit 7 = pump 8.
        """
        registers = await self.read_registers(REGISTER_PUMP_ACTIVE, 1)
        if registers is None:
            return None
        bitmask = registers[0]
        return {i + 1: bool(bitmask & (1 << i)) for i in range(8)}

    async def _read_zone_bitmask(self, start_register: int, count: int) -> dict[int, bool] | None:
        """Generic zone bitmask reader for 64 zones across 4 registers.

        Each register contains 16 bits, with bit 0 of register 0 being zone 0,
        bit 15 of register 0 being zone 15, bit 0 of register 1 being zone 16, etc.

        Returns dict of zone_id (0-63) -> is_active (True/False).
        """
        registers = await self.read_registers(start_register, count)
        if registers is None:
            return None

        result: dict[int, bool] = {}
        for reg_idx, reg_value in enumerate(registers):
            for bit in range(16):
                zone_id = reg_idx * 16 + bit
                result[zone_id] = bool(reg_value & (1 << bit))
        return result

    async def read_humidity_request(self) -> dict[int, bool] | None:
        """Read humidity request bitmasks (registers 2896-2899).

        Returns dict of zone_id (0-63) -> is_requesting (True/False).
        """
        return await self._read_zone_bitmask(
            REGISTER_HUMIDITY_REQUEST_START, REGISTER_HUMIDITY_REQUEST_COUNT
        )

    async def read_ventilation_request(self) -> dict[int, bool] | None:
        """Read ventilation request bitmasks (registers 2900-2903).

        Returns dict of zone_id (0-63) -> is_requesting (True/False).
        """
        return await self._read_zone_bitmask(
            REGISTER_VENTILATION_REQUEST_START, REGISTER_VENTILATION_REQUEST_COUNT
        )

    async def read_renewal_request(self) -> dict[int, bool] | None:
        """Read renewal request bitmasks (registers 2904-2907).

        Returns dict of zone_id (0-63) -> is_requesting (True/False).
        """
        return await self._read_zone_bitmask(
            REGISTER_RENEWAL_REQUEST_START, REGISTER_RENEWAL_REQUEST_COUNT
        )

    async def read_integration_request(self) -> dict[int, bool] | None:
        """Read integration request bitmasks (registers 2908-2911).

        Returns dict of zone_id (0-63) -> is_requesting (True/False).
        """
        return await self._read_zone_bitmask(
            REGISTER_INTEGRATION_REQUEST_START, REGISTER_INTEGRATION_REQUEST_COUNT
        )

    async def read_dehumidification_pump(self) -> dict[int, bool] | None:
        """Read dehumidification pump bitmasks (registers 2912-2915).

        Returns dict of zone_id (0-63) -> is_active (True/False).
        """
        return await self._read_zone_bitmask(
            REGISTER_DEHUMIDIFICATION_PUMP_START, REGISTER_DEHUMIDIFICATION_PUMP_COUNT
        )
