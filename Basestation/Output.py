"""Implements helper functions for the console output of the Basestation system."""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
from time import sleep
import art
import termcolor

# import Basestation modules
from Basestation import Globals, Settings


def display_application_title(title):
    """Display the application title as ASCII art over multiple lines.

    Args:
      title(str): title of application

    """
    words = title.split()
    for word in words:
        art.tprint(word + '\n')
        sleep(1)


def print_bold(text):
    """Print `text` in **bold**.

    Args:
      text(str): text to print in bold

    """
    print(termcolor.colored(text, attrs=['bold']))


def show_state():
    """Print the current values of global variables `Global.smartpatch_config_update`, `Globals.mac_address_update`,
    and `Globals.patient_mapping`.

    """

    print_bold('\nCurrent System State:')
    if Globals.patient_mapping:
        print(f'SmartPatch-Patient-Mapping: {Globals.patient_mapping}')
    else:
        print('There are no devices connected at the moment.')
    if Globals.smartpatch_config_update or Globals.mac_address_update:
        print_bold('Newest updates to the system state:')
        if Globals.smartpatch_config_update:
            print(f'SmartPatch-Configuration-Update: {Globals.smartpatch_config_update}')
        if Globals.mac_address_update:
            print(f'Connection update: {Globals.mac_address_update}')
    else:
        print("There were no new updates to the system state.")


def show_configuration():
    """Print the current  Basestation configuration values.

    """
    print_bold('\nCurrent Basestation Configuration:')
    print(f'Publishing to Thingsboard Server: {"Enabled" if Settings.PUBLISH_TO_THINGSBOARD else "Disabled"}')
    print(f'Saving Data on Basestation: {"Enabled" if Settings.LOCAL_DATA_LOGGING else "Disabled"}')
    print(f'Saving Raw Data on Basestation: {"Enabled" if Settings.SAVE_RAW_DATA else "Disabled"}')
    print(f'Publishing Raw Data to Thingsboard Server: {"Enabled" if Settings.PUBLISH_RAW_DATA else "Disabled"}')
    print(f'Processing Data on Basestation: {"Enabled" if Settings.PROCESS_DATA else "Disabled"}')


def ready_message():
    """Print that the Basestation is now activated and display a link to the Thingsboard server.

    """
    print_bold(f'\n{Settings.BASESTATION_NAME} is activated and awaiting connections!')
    print_bold('Access the data collected from this Basestation on the SmartPatch Data Visualization Platform:')
    print_bold(f'{Settings.URL}')
    print_bold('Change Patient-SmartPatch connections using the SmartPatch Connector App available on Android and iOs.')
