# RDZ HMI Control - Home Assistant Integration

A custom Home Assistant integration for controlling RDZ HMI thermostats via Modbus TCP.

## Overview

This integration connects to RDZ HMI HVAC control systems over Modbus TCP and exposes thermostats as Home Assistant climate entities. The system supports up to 64 zones with separate heating (winter) and cooling (summer) setpoints.

## Key Concepts

### Season Mode (Global)
The system operates in one of two modes controlled by a global season switch:
- **Winter Mode**: System is in heating mode, thermostats show heating action
- **Summer Mode**: System is in cooling mode, thermostats show cooling action

The season switch controls Modbus coil 2 and affects all thermostats globally. Individual thermostats cannot override the season - their HVAC mode/action is derived from this switch.

### Thermostat Types
Zones can be configured as one of three types:

1. **Real Thermostat** (`real`): Physical thermostat with temperature sensor
   - Supports setting target temperature
   - HVAC mode is read-only (derived from season switch)
   - Can be linked to a virtual thermostat for setpoint syncing

2. **Virtual Thermostat** (`virtual`): Software-controlled zone without physical thermostat
   - Read-only (no direct control)
   - Can be linked from a real thermostat to auto-sync setpoints

3. **Unconfigured** (`unconfigured`): Detected zone not yet configured
   - Shows as OFF, no control available

### Setpoints
Each zone has two temperature setpoints stored in separate Modbus registers:
- **Winter Setpoint** (registers 300-363): Used when system is in heating mode
- **Summer Setpoint** (registers 364-427): Used when system is in cooling mode

When you change the target temperature, it writes to the appropriate setpoint based on the current season.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant                            │
├─────────────────────────────────────────────────────────────┤
│  __init__.py          Entry point, platform setup           │
│  coordinator.py       Data polling, setpoint syncing        │
│  climate.py           Climate entities (thermostats)        │
│  humidifier.py        Dehumidifier entities (humidity ctrl) │
│  switch.py            Season + system activation switches   │
│  select.py            Zone mode select entities             │
│  sensor.py            Setpoint, temperature, dew point      │
│  binary_sensor.py     Pump active sensors                   │
│  number.py            Time setting entities                 │
│  modbus_client.py     Async Modbus TCP communication        │
│  config_flow.py       UI configuration wizard               │
│  const.py             Constants and register addresses      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Modbus TCP (default port 8000)
                              ▼
                    ┌─────────────────┐
                    │   RDZ HMI       │
                    │   Controller    │
                    └─────────────────┘
```

## File Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Integration setup, platform loading, lifecycle management |
| `coordinator.py` | `RDZDataUpdateCoordinator` - polls Modbus every 30s, syncs linked thermostats |
| `climate.py` | `RDZClimateEntity` - thermostat entities with season-based HVAC mode |
| `humidifier.py` | `RDZDehumidifierEntity` - dehumidifier control with humidity setpoints |
| `switch.py` | `RDZSeasonSwitch` + `RDZSystemActivationSwitch` - season and system control |
| `select.py` | `RDZZoneModeSelect` - zone mode selection (Off/Man/Pgm/Pgm-Man) |
| `sensor.py` | `RDZSetpointSensor`, `RDZDewPointSensor`, `RDZOutsideTemperatureSensor`, `RDZWaterTemperatureSensor` |
| `binary_sensor.py` | `RDZPumpActiveBinarySensor` - pump running status |
| `number.py` | `RDZTimeSettingNumber` - system time configuration |
| `modbus_client.py` | `RDZModbusClient` - async Modbus TCP wrapper with connection management |
| `config_flow.py` | Configuration UI for adding/configuring the integration |
| `const.py` | Constants: register addresses, defaults, config keys |

## Modbus Register Map

### Zone Registers

| Register/Coil | Address | Description |
|---------------|---------|-------------|
| Coil 2 | 2 | Season (0=winter, 1=summer) |
| Registers 300-363 | 300 + zone_id | Winter setpoints (value * 10) |
| Registers 364-427 | 364 + zone_id | Summer setpoints (value * 10) |
| Registers 428-491 | 428 + zone_id | Dehumidification setpoints (raw %, no scaling) |
| Registers 2700-2763 | 2700 + zone_id | Current temperatures (value * 10, read-only) |
| Registers 2828-2891 | 2828 + zone_id | Dew point temperatures (value * 10, read-only) |
| Registers 2892-2895 | 2892 + (zone_id / 16) | Zone activity bitmasks (16-bit, read-only) |
| Registers 5301-5364 | 5301 + zone_id | Zone mode (0=Off, 1=Man, 2=Pgm, 3=Pgm/Man) |
| Registers 7701-7764 | 7701 + zone_id | Current humidity (value * 10, read-only) |

### System Registers

| Register/Coil | Address | Description |
|---------------|---------|-------------|
| Coils 100-107 | 100 + (system_id - 1) | System activation (1-8) |
| Register 2600 | 2600 | Outside temperature (value * 10, read-only) |
| Registers 2650-2657 | 2650 + (system_id - 1) | Delivery water temperatures 1-8 (value * 10, read-only) |
| Registers 2658-2665 | 2658 + (system_id - 1) | Calculated water temperatures 1-8 (value * 10, read-only) |
| Registers 5009-5013 | 5009-5013 | Time settings: Day, Month, Year, Hour, Minute |
| Register 7615 | 7615 | Pump active bitmask (bit 0 = pump 1, read-only) |

Temperature values are stored as integers with a scale factor of 10 (e.g., 21.5°C = 215).

### Zone Activity Bitmasks
Registers 2892-2895 contain 16-bit bitmasks indicating which zones are actively heating/cooling:
- **Register 2892**: Zones 0-15 (bit 0 = zone 0, bit 15 = zone 15)
- **Register 2893**: Zones 16-31 (bit 0 = zone 16, bit 15 = zone 31)
- **Register 2894**: Zones 32-47 (bit 0 = zone 32, bit 15 = zone 47)
- **Register 2895**: Zones 48-63 (bit 0 = zone 48, bit 15 = zone 63)

Bit = 1: Zone is actively heating/cooling
Bit = 0: Zone is idle

### Pump Active Bitmask
Register 7615 contains an 8-bit bitmask indicating which pumps are currently running:
- Bit 0: Pump 1 active
- Bit 1: Pump 2 active
- ...
- Bit 7: Pump 8 active

Bit = 1: Pump is running
Bit = 0: Pump is idle

## Data Flow

### Reading Data (Coordinator)
1. Every 30 seconds, coordinator polls:
   - All temperature registers (2700-2763)
   - Winter setpoints (300-363)
   - Summer setpoints (364-427)
   - Dehumidification setpoints (428-491)
   - Humidity values (7701-7764)
   - Dew point temperatures (2828-2891)
   - Zone modes (5301-5364)
   - Season coil (2)
   - Zone activity bitmasks (2892-2895)
   - Outside temperature (2600)
   - Time settings (5009-5013)
   - System activation coils (100-107)
   - Delivery water temperatures (2650-2657)
   - Calculated water temperatures (2658-2665)
   - Pump active bitmask (7615)
2. Data stored in `coordinator.data` dictionary
3. Entities update via `_handle_coordinator_update()`

### Setting Temperature
1. User changes target temperature on climate entity
2. `async_set_temperature()` determines current season from coordinator data
3. Writes to winter (HEAT) or summer (COOL) setpoint register
4. If real thermostat is linked to virtual, coordinator syncs on next poll

### Changing Season
1. User toggles season switch
2. `async_turn_on()`/`async_turn_off()` writes to coil 2
3. All climate entities update their HVAC mode accordingly

### HVAC Action Detection
The HVAC action (heating/cooling/idle) is determined from the zone activity bitmasks:

For **real thermostats**:
- **HEATING**: The zone's bit is set (1) in the activity bitmask
- **COOLING**: The linked virtual zone's bit is set (1) in the activity bitmask
- **IDLE**: Neither this zone nor linked virtual zone is active

For **virtual/unconfigured thermostats**: Always shows OFF

## Entities Created

For each configured zone:
- 1x Climate entity (thermostat)
- 1x Winter setpoint sensor (diagnostic)
- 1x Summer setpoint sensor (diagnostic)
- 1x Dew point sensor (diagnostic)

System-level (on the "RDZ HMI System" device):
- 1x Season switch (summer/winter mode)
- 8x System activation switches (System 1-8)
- 1x Outside temperature sensor
- 8x Delivery water temperature sensors (1-8)
- 8x Calculated water temperature sensors (1-8)
- 8x Pump active binary sensors (1-8)
- 5x Time setting number entities (Day, Month, Year, Hour, Minute)

## Configuration

The integration is configured through the Home Assistant UI:
1. Add integration, enter Modbus host/port
2. Integration discovers active zones (non-zero temperature readings)
3. Configure each zone: name, type (real/virtual/unconfigured)
4. Optionally link real thermostats to virtual zones for setpoint syncing