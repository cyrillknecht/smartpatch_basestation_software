"""
Implements the Mapping thread used in Basestation.py and some functions that run to initialize the Basestation.

Provides all functionality to work with the SmartPatch Connector App.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# importing libraries
import logging
from tb_device_mqtt import TBDeviceMqttClient
from tb_rest_client.rest import ApiException
from tb_rest_client.rest_client_ce import *
from tqdm import tqdm

# importing Basestation modules
from Basestation import Globals, Output, Settings


def get_config(attribute_keys='publishToThingsboard,saveRawData,publishRawData,processData,'
                              'localDataLogging,SmartPatchConfig',
               basestation_name=Settings.BASESTATION_NAME,
               api_url=Settings.URL, username=Settings.USERNAME,
               password=Settings.PASSWORD):
    """Return dict with Basestation and SmartPatch configuration fetched from Thingsboard database.
    
    Fetch current configuration attributes from Thingsboard database. Add them to dict.
    Log and print error message when failed.

    Args:
      attribute_keys(str, optional): all attribute names to fetch, separated by decimal points, no whitespaces
                                     (Default value = 'publishToThingsboard,saveRawData,publishRawData,processData,'
                                                      'localDataLogging,SmartPatchConfig')
      basestation_name(str, optional): name of this Basestation (Default value = Settings.BASESTATION_NAME)
      api_url(str, optional): URL of Thingsboard server (Default value = Settings.URL)
      username(str, optional): username for Thingsboard server (Default value = Settings.USERNAME)
      password(str, optional): password for Thingsboard server (Default value = Settings.PASSWORD)

    Returns:
      dict: dict with attribute_keys as keys and their current values from Thingsboard database as values

    """
    configuration = {}
    with RestClientCE(api_url) as rest_client:
        try:
            rest_client.login(username, password)
            basestation = rest_client.get_tenant_device(basestation_name)
            try:
                response = rest_client.get_attributes(entity_type='DEVICE',
                                                      entity_id=basestation.id.id,
                                                      keys=attribute_keys)
                for attribute in response:
                    configuration[attribute['key']] = attribute['value']

            except Exception as e:
                logging.exception(f'{e}: Failed to fetch custom configuration. An attribute was not defined yet.')
                print(f'No custom Basestation configuration found. Basestation will run with default configuration.')
                configuration = {}
        except ApiException as e:
            logging.exception(e)
    return configuration


def set_new_config(config_dict):
    """Set the configuration settings from a configuration dict.
    
       Watch out, keys of config dict have to be in the right
       order. Depends highly on get_config.

    Args:
      config_dict(dict: dict): dict of configuration, provide it with get_config

    """
    if 'publishToThingsboard' in config_dict:
        Settings.PUBLISH_TO_THINGSBOARD = config_dict['publishToThingsboard']
    if 'saveRawData' in config_dict:
        Settings.SAVE_RAW_DATA = config_dict['saveRawData']
    if 'publishRawData' in config_dict:
        Settings.PUBLISH_RAW_DATA = config_dict['publishRawData']
    if 'processData' in config_dict:
        Settings.PROCESS_DATA = config_dict['processData']
    if 'localDataLogging' in config_dict:
        Settings.LOCAL_DATA_LOGGING = config_dict['localDataLogging']
    if 'SmartPatchConfig' in config_dict:
        with Globals.config_update_lock:
            Globals.smartpatch_config_update = config_dict['SmartPatchConfig']


def get_patient_mapping(api_url, username, password, max_patients):
    """Return dict with SmartPatch MAC addresses as keys and assigned patient names as values from Thingsboard database.

    Args:
      api_url(str): URL of Thingsboard server
      username(str): username for Thingsboard server
      password(str): password for Thingsboard server
      max_patients(int): maximum patients that will be fetched

    Returns:
      dict: mapping with MAC addresses as keys and patient-names as values

    """
    patient_mapping = {}
    with RestClientCE(api_url) as rest_client:
        try:
            rest_client.login(username, password)
            res = rest_client.get_tenant_devices(page_size=str(max_patients), type='Patient', page=str(0))
            for patient_data in tqdm(res.data, leave=False, unit='Patient'):
                # catch exception when patient was not created correctly and therefore has no mac-address
                try:
                    response = rest_client.get_attributes(entity_type='DEVICE',
                                                          entity_id=patient_data.id.id,
                                                          keys='Mac-Address')
                    if response:  # check if there is even a MAC Address
                        if response[0]['value'] != 'disconnected':
                            patient_mapping[response[0]['value']] = patient_data.name

                except Exception as e:
                    logging.exception(f'{e}: Problem with fetching initial patient mapping.')
        except ApiException as e:
            logging.exception(e)
    return patient_mapping


def get_matching_device(mac_address, current_device_mapping):
    """Return the device accesstoken that matches the given MAC address.

    Args:
      mac_address(str): MAC address of SmartPatch
      current_device_mapping(dict): device mapping obtained with `get_patient_mapping`

    Returns:
      str|None: patient name for given MAC address or None if no patient name was found

    """
    if mac_address in current_device_mapping:
        return current_device_mapping[mac_address]

    else:
        print(f'No matching patient for {mac_address} found.')

    return None


def basestation_config_update(update):
    """Print received Basestation configuration update and explain how to apply the update.

    Args:
      update(dict): message received from callback on_update

    """
    print('\nNew Update to Basestation configuration:')
    print(update)
    print("To apply this Basestation configuration update, please restart the Basestation.")


def smartpatch_config_update(update_content):
    """Update global variable `Globals.smartpatch_config_update` to update_content.

    Args:
      update_content(dict): content of update received from callback `on_update`

    """
    with Globals.config_update_lock:
        Globals.smartpatch_config_update = update_content


def disconnect_update(mac_address):
    """Update globals variables `Globals.patient_mapping` and `Globals.mac_address_update` to indicate that
    SmartPatch should get disconnected from Basestation.

    Args:
      mac_address(str): MAC address obtained from update message received from callback `on_update`

    """
    # add entry to mac_address_update dict
    if mac_address != 'disconnected':  # if device was already disconnected before, there would be no need to remove it
        with Globals.mac_address_update_lock:
            Globals.mac_address_update[mac_address] = 'remove'

    # remove disconnected entry from the patient mapping
    with Globals.patient_mapping_lock:
        if mac_address in Globals.patient_mapping:
            Globals.patient_mapping.pop(mac_address)


def connect_update(patient_name, mac_address):
    """Update global variables `Globals.patient_mapping` and `Globals.mac_address_update` and cleans up old connections
       to indicate that SmartPatch should get connected to Basestation.

    Args:
      patient_name(str): patient name obtained from update message received from callback `on_update`
      mac_address(str): MAC address obtained from update message received from callback `on_update`

    """
    # deleting old connections if necessary
    with Globals.patient_mapping_lock and Globals.mac_address_update_lock:

        # check if the patient was already connected
        if patient_name in Globals.patient_mapping.values():

            # gather previous connections
            to_delete = []
            for address in Globals.patient_mapping:
                if Globals.patient_mapping[address] == patient_name:
                    to_delete.append(address)

            # delete previous connections
            for previous_address in to_delete:
                Globals.patient_mapping.pop(previous_address)
                Globals.mac_address_update[previous_address] = 'remove'

        # adding/updating entry in patient mapping
        Globals.patient_mapping[mac_address] = patient_name
        # adding entry to mac_address_update_dict
        Globals.mac_address_update[mac_address] = 'add'


def on_update(_, update, __):
    """Callback when an update from the Connector app is detected on thingsboard server.
    
    Updates global variables smartpatch_config_update, mac_address_update and patient_mapping according to
    received update.

    Args:
      _: placeholder for callback argument
      update(dict): message from Thingsboard server on update to subscribed MQTT topics.
      __: placeholder for callback argument

    """

    # unpacking the received update
    update_topic = list(update.keys())[0]
    update_content = list(update.values())[0]

    # check for Basestation configuration update
    if update_topic in Settings.BASESTATION_CONFIG_PARAMS_LIST:
        basestation_config_update(update)
        # if the update is a change to the Basestation configuration, we do not need to see the system state
        return

    print(f'\nNew update of type: {update_topic}')
    # check for SmartPatch configuration update
    if update_topic == 'SmartPatchConfig':
        smartpatch_config_update(update_content)

    else:
        # dissect update further
        patient_name = list(update_content.keys())[0]
        macAddress = list(update_content.values())[0]

        # checks if update is a disconnect
        if update_topic == 'Disconnected':
            disconnect_update(macAddress)

        # checks if update is a connect
        elif update_topic == 'Connected':
            connect_update(patient_name, macAddress)

        # update could not be assigned
        else:
            print('Not a valid update.')

    # print the changed state of the system
    Output.show_state()


def get_updates(attribute_list, device_name=Settings.BASESTATION_NAME, callback=on_update, broker=Settings.BROKER, ):
    """Initialize a connection to thingsboard and subscribe to updates for attributes.

    Args:
      attribute_list(list: list): all Thingsboard attributes to subscribe to
      device_name(str, optional): device name on Thingsboard from which you want to subscribe to attributes (Default value = Settings.BASESTATION_NAME)
      broker(str, optional): IP address of Thingsboard server (Default value = Settings.BROKER)
      callback(Callable, optional): callback function when an update is received (Default value = on_update)

    """

    # connecting to thingsboard updater device
    client = TBDeviceMqttClient(host=broker, token=device_name)
    client.connect()

    # subscribing to the different update attributes
    for attribute in attribute_list:
        client.subscribe_to_attribute(key=attribute, callback=callback)
    while True:
        sleep(1000)


def configure_basestation():
    """Fetch the current configurations for the Basestation and its connected SmartPatches from the Thingsboard
    database and apply them.
    
    Function is only effective on basestation startup.

    """
    current_configuration = get_config(api_url=Settings.URL, username=Settings.USERNAME, password=Settings.PASSWORD)
    set_new_config(current_configuration)


def patient_mapping_loop():
    """Initialize `Globals.mac_address_update` and `Globals.patient_mapping` and update it on new update.
    
       Main function for `Mapping thread`. Apply any new update and then print the updated system state.
       Loop endlessly while waiting for updates.

    """
    try:
        with Globals.patient_mapping_lock:
            # creating initial patient_mapping on startup
            Globals.patient_mapping = get_patient_mapping(api_url=Settings.URL,
                                                          username=Settings.USERNAME,
                                                          password=Settings.PASSWORD,
                                                          max_patients=Settings.MAX_PATIENTS)
            # creating initial mac_adress_update dict on startup
            with Globals.mac_address_update_lock:
                for macAddress in Globals.patient_mapping:
                    Globals.mac_address_update[macAddress] = 'add'

        # print the changed state of the system
        Output.show_state()

        # waiting for updates
        get_updates(broker=Settings.BROKER,
                    device_name=Settings.BASESTATION_NAME,
                    attribute_list=Settings.UPDATE_ATTRIBUTES_LIST,
                    callback=on_update)
    except ApiException as exception:
        logging.exception(exception)
