"""
## Settings for the Basestation

Set Broker to your Thingsboard Server IP address.
Adjust Username and Password, if they were changed from the default values.

The Basestation configuration flags can also be changed on the **SmartPatch Admin UI**.

"""

# import libraries
import logging
from time import time

# Software version of Basestation
SOFTWARE_VERSION = '1.0.0'
BASESTATION_NAME = 'AddYourBasestationName'

# Settings for Thingsboard server
BROKER = 'AddYourServerIpAddress'  # host name, has to be updated every time for localhost
PORT = 1883  # data listening port

# Settings for ThingsBoard REST API
URL = 'http://' + BROKER + ':8080'
USERNAME = 'tenant@thingsboard.org'
PASSWORD = 'tenant'

# Settings for Basestation
INITIALIZATION_DELAY = 1  # time between trying to initialize Threads
PROCESSING_DELAY = 0.05  # time between trying to fetch new data for data processing
PUBLISHING_DELAY = 0.05  # time between publications to Thingsboard server

MAX_PATIENTS = 100  # maximum number of devices supported

# Settings for BLE
DEVICE_MAXIMUM = 10  # limit of connectable devices per base station

# Settings for MQTT
UPDATE_ATTRIBUTES_LIST = ['Connected', 'Disconnected', 'SmartPatchConfig', 'publishToThingsboard', 'saveRawData',
                          'publishRawData', 'processData', 'localDataLogging', 'SmartPatchConfig']
BASESTATION_CONFIG_PARAMS_LIST = ['publishToThingsboard', 'saveRawData', 'publishRawData', 'processData',
                                  'localDataLogging']
# Paths
LOG_FILE_PATH = 'Logs/'
BACKUP_LOG_PATH = LOG_FILE_PATH + 'BackupData/'
RAW_LOG_PATH = LOG_FILE_PATH + 'RawData/'
RUNTIME_LOG_PATH = LOG_FILE_PATH + 'Runtime/'

# Default Basestation configuration flags
PROCESS_DATA = True
PUBLISH_TO_THINGSBOARD = True
LOCAL_DATA_LOGGING = False  # only gets executed if PUBLISH_TO_THINGSBOARD is set to False
SAVE_RAW_DATA = False
PUBLISH_RAW_DATA = False

# Global exception logging configuration
logging.basicConfig(level=logging.INFO, filename=RUNTIME_LOG_PATH + str(round(time())) + '.log')
