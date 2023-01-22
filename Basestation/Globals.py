"""Collection of all global variables used in Basestation software"""

# import libraries
import threading

# addresses of currently connected devices
connected_devices = {}

# global variables for updates
mac_address_update = {}
patient_mapping = {}
smartpatch_config_update = 0

# global variables for passing input_data
unprocessed_data = {}
processed_data = {}

# global locks
connected_devices_lock = threading.Lock()
mac_address_update_lock = threading.Lock()
patient_mapping_lock = threading.Lock()
config_update_lock = threading.Lock()

unprocessed_data_lock = threading.Lock()
processed_data_lock = threading.Lock()
