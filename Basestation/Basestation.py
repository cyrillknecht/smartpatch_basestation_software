"""
Main Basestation application.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# importing libraries
import asyncio
import threading
from time import sleep

# importing Basestation modules
from Basestation import DataProcessing, Ble, Mapping, Globals, Output, SaveLocally, PublishToThingsboard, Settings


# functions for threads:
def get_current_device_mapping():
    """Thread gets a current dict of all patients with their connected SmartPatches MAC addresses as value and makes it
        accessible as global dict patient_mapping.
        Writes any changes to active MAC addresses into global dict `Globals.mac_address_update`.
    """
    Mapping.patient_mapping_loop()


def get_ble_data():
    """Thread gets sensor input_data over BLE from MAC addresses specified in global dict MAC address_update.
        Writes received input_data into global dict unprocessed_data.
    """
    asyncio.run(Ble.ble_loop())


def process_data():
    """Thread takes input_data from global dict `Globals.unprocessed_data`, processes it if necessary and writes the
    resulting input_data into global dict `Globals.processed_data`. Deletes the already processed entries from
    `Globals.unprocessed_data` dict.
    """
    # check if input_data processing in Basestation is needed
    if not Settings.PROCESS_DATA:
        print(f'Warning: Your SmartPatch input_data will not be processed which could possibly lead to problems '
              f'with saving it to a Thingsboard server.\n'
              f'If you want to save your raw SmartPatch input_data, please choose dedicated RAW_DATA_LOGGING option.')
        DataProcessing.no_data_processing()
    else:
        asyncio.run(DataProcessing.data_processing())


def publish_to_thingsboard():
    """Thread publishes processed input_data from global dict processed_data to Thingsboard.
       Deletes already published entries from said dict.
    """
    # check if input_data should be published to Thingsboard server (preferred option)
    if Settings.PUBLISH_TO_THINGSBOARD:
        print(f'Saving SmartPatch data on Thingsboard server with URL: {Settings.URL}.')
        PublishToThingsboard.publishing_loop()

    # if not, check if input_data should be logged to a local csv file
    elif Settings.LOCAL_DATA_LOGGING:
        print(f'Saving SmartPatch data to local csv files at target directory {Settings.BACKUP_LOG_PATH} on'
              f'Basestation.')
        SaveLocally.local_logging_loop()

    # warn the user if no option was selected
    else:
        print('Warning: SmartPatch data is not saved anywhere.\n This will lead to an eventual crash of the '
              'Basestation software.')


def save_raw_data():
    """Thread saves raw sensor input_data received over BLE to a local csv."""
    print(f'Saving raw SmartPatch input_data to csv files at target directory {Settings.RAW_LOG_PATH} '
          f'on Basestation.\nThis does not impact other input_data saving options.')
    if Settings.PUBLISH_RAW_DATA:
        PublishToThingsboard.raw_data_publishing_loop()
    else:
        SaveLocally.raw_data_logging_loop()


# main application
def main():
    """Run main Basestation application.
    
    Initialize from Basestation configuration fetched from Thingsboard server.
    Map patients to SmartPatches. Connect/Disconnect from SmartPatches.
    Read their sensor input_data and publish or save it to a Target chosen in the configuration.
    Continuously wait for updates for patient-SmartPatch-mapping or SmartPatch-configuration and apply them.
    """

    Output.display_application_title(f'SmartPatch Basestation v{Settings.SOFTWARE_VERSION}')

    Output.print_bold('Initializing threads..')

    # initializing threads
    BLE_Thread = threading.Thread(target=get_ble_data)

    Mapping_Thread = threading.Thread(target=get_current_device_mapping)

    Publishing_Thread = threading.Thread(target=publish_to_thingsboard)

    Processing_Thread = threading.Thread(target=process_data)

    Raw_Data_Thread = threading.Thread(target=save_raw_data)

    # fetching configuration from Thingsboard database
    Output.print_bold('\nFetching Basestation configuration..')
    Mapping.configure_basestation()
    Output.show_configuration()

    # starting threads
    Output.print_bold('\nMapping patients and SmartPatches..')
    Mapping_Thread.start()

    Output.ready_message()

    # waiting for non-empty device mapping before continuing
    while not Globals.patient_mapping:
        sleep(Settings.INITIALIZATION_DELAY)

    Output.print_bold('\nStart connecting to SmartPatches..')
    BLE_Thread.start()

    # waiting for first received SmartPatch input_data before continuing
    while not Globals.unprocessed_data:
        sleep(Settings.INITIALIZATION_DELAY)

    Output.print_bold('\nStart processing received data..')
    Processing_Thread.start()

    # waiting for first processed SmartPatch input_data before continuing
    while not Globals.processed_data:
        sleep(Settings.INITIALIZATION_DELAY)

    if Settings.SAVE_RAW_DATA:
        Output.print_bold('\nStart saving raw data..')
        Raw_Data_Thread.start()

    Output.print_bold('\nStart saving data..')
    Publishing_Thread.start()
