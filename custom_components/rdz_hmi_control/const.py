"""Constants for RDZ HMI Control integration."""

DOMAIN = "rdz_hmi_control"

# Modbus connection defaults
DEFAULT_PORT = 8000
DEFAULT_SCAN_INTERVAL = 30

# Modbus register addresses
REGISTER_TEMP_START = 2700
REGISTER_TEMP_COUNT = 64

REGISTER_WINTER_SETPOINT_START = 300
REGISTER_WINTER_SETPOINT_COUNT = 64

REGISTER_SUMMER_SETPOINT_START = 364
REGISTER_SUMMER_SETPOINT_COUNT = 64

# Coil addresses
COIL_SEASON = 2  # 0 = winter, 1 = summer

# Activity bitmask registers (4 registers, 16 bits each = 64 zones)
REGISTER_ACTIVITY_START = 2892
REGISTER_ACTIVITY_COUNT = 4

# Zone request bitmask registers (4 registers each, 16 bits = 64 zones)
REGISTER_HUMIDITY_REQUEST_START = 2896
REGISTER_HUMIDITY_REQUEST_COUNT = 4

REGISTER_VENTILATION_REQUEST_START = 2900
REGISTER_VENTILATION_REQUEST_COUNT = 4

REGISTER_RENEWAL_REQUEST_START = 2904
REGISTER_RENEWAL_REQUEST_COUNT = 4

REGISTER_INTEGRATION_REQUEST_START = 2908
REGISTER_INTEGRATION_REQUEST_COUNT = 4

REGISTER_DEHUMIDIFICATION_PUMP_START = 2912
REGISTER_DEHUMIDIFICATION_PUMP_COUNT = 4

# Humidity registers
REGISTER_HUMIDITY_START = 7701
REGISTER_HUMIDITY_COUNT = 64

# Summer dehumidification setpoint registers
REGISTER_DEHUMIDIFICATION_SETPOINT_START = 428
REGISTER_DEHUMIDIFICATION_SETPOINT_COUNT = 64

# Dew point registers
REGISTER_DEW_POINT_START = 2828
REGISTER_DEW_POINT_COUNT = 64

# Zone mode registers
REGISTER_ZONE_MODE_START = 5301
REGISTER_ZONE_MODE_COUNT = 64

# Zone mode values
ZONE_MODE_OFF = 0
ZONE_MODE_MAN = 1
ZONE_MODE_PGM = 2
ZONE_MODE_PGM_MAN = 3

ZONE_MODE_OPTIONS = {
    ZONE_MODE_OFF: "Off",
    ZONE_MODE_MAN: "Man",
    ZONE_MODE_PGM: "Pgm",
    ZONE_MODE_PGM_MAN: "Pgm/Man",
}

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_ZONES = "zones"

# Zone config keys
CONF_ZONE_ID = "zone_id"
CONF_ZONE_NAME = "name"
CONF_ZONE_TYPE = "type"
CONF_LINKED_VIRTUAL_ZONE = "linked_virtual_zone"
CONF_HVAC_MODE = "hvac_mode"

# Thermostat types
THERMOSTAT_TYPE_REAL = "real"
THERMOSTAT_TYPE_VIRTUAL = "virtual"
THERMOSTAT_TYPE_UNCONFIGURED = "unconfigured"

# Data keys in coordinator
DATA_TEMPERATURES = "temperatures"
DATA_WINTER_SETPOINTS = "winter_setpoints"
DATA_SUMMER_SETPOINTS = "summer_setpoints"
DATA_SEASON = "season"  # True = summer, False = winter
DATA_ZONE_ACTIVITY = "zone_activity"  # dict[int, bool] - zone_id -> is_active
DATA_HUMIDITY_REQUEST = "humidity_request"
DATA_VENTILATION_REQUEST = "ventilation_request"
DATA_RENEWAL_REQUEST = "renewal_request"
DATA_INTEGRATION_REQUEST = "integration_request"
DATA_DEHUMIDIFICATION_PUMP = "dehumidification_pump"
DATA_HUMIDITY = "humidity"
DATA_DEHUMIDIFICATION_SETPOINTS = "dehumidification_setpoints"
DATA_DEW_POINTS = "dew_points"
DATA_ZONE_MODES = "zone_modes"

# Temperature scale factor (Modbus returns values * 10)
TEMP_SCALE_FACTOR = 10.0

# Min/Max temperature limits
MIN_TEMP = 5.0
MAX_TEMP = 35.0
TEMP_STEP = 0.5

# Humidity limits
MIN_HUMIDITY = 30
MAX_HUMIDITY = 90

# Outside temperature register
REGISTER_OUTSIDE_TEMP = 2600

# Time settings registers (Day, Month, Year, Hour, Minute)
REGISTER_TIME_DAY = 5009
REGISTER_TIME_MONTH = 5010
REGISTER_TIME_YEAR = 5011
REGISTER_TIME_HOUR = 5012
REGISTER_TIME_MINUTE = 5013

# System activation coils
COIL_SYSTEM_ACTIVATION_START = 100
COIL_SYSTEM_ACTIVATION_COUNT = 8

# Water temperature registers
REGISTER_DELIVERY_WATER_TEMP_START = 2650
REGISTER_DELIVERY_WATER_TEMP_COUNT = 8
REGISTER_CALCULATED_WATER_TEMP_START = 2658
REGISTER_CALCULATED_WATER_TEMP_COUNT = 8

# Pump active bitmask register
REGISTER_PUMP_ACTIVE = 7615

# Data keys for new features
DATA_OUTSIDE_TEMP = "outside_temperature"
DATA_TIME_SETTINGS = "time_settings"
DATA_SYSTEM_ACTIVATION = "system_activation"
DATA_DELIVERY_WATER_TEMPS = "delivery_water_temps"
DATA_CALCULATED_WATER_TEMPS = "calculated_water_temps"
DATA_PUMP_ACTIVE = "pump_active"
