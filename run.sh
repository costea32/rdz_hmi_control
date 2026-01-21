python3 -m venv venv
source venv/bin/activate
pip install homeassistant

# Create config directory structure
mkdir -p config/custom_components
ln -s $(pwd)/custom_components/rdz_hmi_control config/custom_components/

# Run Home Assistant
hass -c config