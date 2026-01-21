# RDZ HMI Control for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom Home Assistant integration for controlling RDZ Graphic Tablet (HMI) thermostats via Modbus TCP. This allows you to remotely monitor and control your RDZ HVAC system directly from Home Assistant.

## Features

- Control up to 64 thermostat zones
- Support for both heating (winter) and cooling (summer) modes
- Global season switch to toggle between heating and cooling
- Automatic setpoint synchronization between real and virtual thermostats
- Real-time temperature monitoring

## Prerequisites

- RDZ Graphic Tablet (HMI) connected to your network
- Home Assistant installation
- Network access from Home Assistant to the RDZ tablet on port 8000
- **Important**: All thermostats must be set to **manual mode** on the physical devices

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL and select "Integration" as the category
5. Click "Add"
6. Search for "RDZ HMI Control" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/rdz_hmi_control` folder from this repository
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

Setting up the integration requires identifying and mapping each discovered zone to your physical thermostats. Follow these steps carefully.

### Step 1: Add the Integration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "RDZ HMI Control"
3. Enter the IP address of your RDZ Graphic Tablet
4. Enter port `8000` (default Modbus TCP port for RDZ)
5. Click **Submit**

The integration will discover all active zones from your RDZ system.

### Step 2: Identify Your Thermostats

Since discovered zones are identified only by number, you need to map them to your actual rooms. The easiest way to do this is by using unique setpoint temperatures:

1. Go to each thermostat in rdz tablet
2. Set a unique target temperature for each one:
   - Thermostat 1: 17.1°C
   - Thermostat 2: 17.2°C
   - Thermostat 3: 17.3°C
   - And so on...

3. In Home Assistant, look at the discovered devices:
   - If it's **winter/heating season**: Check the **Winter Setpoint** sensor value
   - If it's **summer/cooling season**: Check the **Summer Setpoint** sensor value

4. Match the setpoint values to identify which zone corresponds to which room

### Step 3: Configure Virtual Thermostats First

Virtual thermostats are used for cooling control. Configure these before real thermostats because you'll need to link them later.

1. Go to **Settings** > **Devices & Services**
2. Find "RDZ HMI Control" and click **Configure**
3. For each virtual thermostat zone:
   - Select the device from the list
   - Set the **Name** to match your room (e.g., "Living Room Cooling")
   - Set **Type** to `virtual`
   - Click **Submit**
4. Repeat for all virtual thermostats

### Step 4: Configure Real Thermostats

Now configure the physical thermostats and link them to their corresponding virtual zones:

1. Go to **Settings** > **Devices & Services**
2. Find "RDZ HMI Control" and click **Configure**
3. For each real thermostat zone:
   - Select the device from the list
   - Set the **Name** to match your room (e.g., "Living Room")
   - Set **Type** to `real`
   - Select the **Linked Virtual Thermostat** (e.g., link "Living Room" to "Living Room Cooling")
   - Click **Submit**
4. Repeat for all real thermostats

### Step 5: Verify Setup

After configuration:

1. The **Season Switch** entity controls whether the system is in heating or cooling mode
2. Each thermostat should display the current temperature
3. Setting a target temperature will:
   - Write to the **winter setpoint** when in heating mode
   - Write to the **summer setpoint** when in cooling mode
4. Linked thermostats will automatically synchronize their setpoints

## Understanding the System

### Season Mode

The RDZ system operates globally in either heating (winter) or cooling (summer) mode. This is controlled by a single switch that affects all thermostats. Individual thermostats cannot override this setting.

### Real vs Virtual Thermostats

- **Real Thermostats**: Physical devices with temperature sensors. These control both heating and cooling but need a linked virtual thermostat for cooling setpoint synchronization.

- **Virtual Thermostats**: Software-controlled zones without physical sensors. These are typically used for cooling-only zones and receive their setpoints from linked real thermostats.

### Setpoint Linking

When you link a real thermostat to a virtual one:
- Changing the temperature on the real thermostat updates both setpoints
- The virtual thermostat's setpoint stays synchronized automatically
- This allows you to use the physical thermostat dial to control cooling temperature

## Troubleshooting

### Thermostats show "Unavailable"
- Verify network connectivity to the RDZ tablet
- Ensure port 8000 is not blocked by a firewall
- Check that the tablet is powered on

### Temperature changes don't take effect
- Confirm thermostats are in **manual mode** on the physical devices
- Check that you're changing the correct setpoint for the current season

### Wrong thermostat responds to commands
- Re-verify the zone mapping using the unique temperature method
- Check that virtual and real thermostats are correctly linked

## Support

For issues and feature requests, please open an issue on the GitHub repository.
