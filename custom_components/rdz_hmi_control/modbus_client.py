"""Async Modbus TCP client wrapper for RDZ HMI Control."""

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    COIL_SEASON,
    REGISTER_ACTIVITY_COUNT,
    REGISTER_ACTIVITY_START,
    REGISTER_TEMP_START,
    REGISTER_TEMP_COUNT,
    REGISTER_WINTER_SETPOINT_START,
    REGISTER_WINTER_SETPOINT_COUNT,
    REGISTER_SUMMER_SETPOINT_START,
    REGISTER_SUMMER_SETPOINT_COUNT,
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
