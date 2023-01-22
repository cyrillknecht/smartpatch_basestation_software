"""
Data logging functionality for creating datasets directly on the Basestation.

Datasets are saved to csv files named with SmartPatch MAC addresses. The module's loggers are only intended as a
backup logging mechanism and therefore provide no special input_data structure in the output files.

"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
import csv
from time import sleep

# import Basestation modules
from Basestation import Globals, Settings


class LocalLogger:
    """Basic logger that lists input_data for devices in a csv file.
    
    Data structure should be as explained in Publishing module description.

    """

    data: dict
    """Special dict structure for datapoints, see `Publishing` module description"""

    log_filepath: str
    """Output directory for datasets."""

    def __init__(self, data, log_filepath):
        """Initialize a Logger with given input_data and output files in directory `log_filepath`.

        Args:
            data(dict): special dict structure for datapoints, see Publishing module description
            log_filepath(str): output directory for datasets

        """
        self.macAddresses = list(data.keys())
        self.data = data
        self.log_filepath = log_filepath

    def write_log(self, mac_address):
        """Add input_data to log in a new row or create new log file if `self.log_filepath/mac_address.csv` does not
        exist already.

        Args:
          mac_address(str): MAC address of a SmartPatch

        """
        # make or open a file with the mac_address as filename
        file_name = self.log_filepath + mac_address + '.csv'
        with open(file_name, 'a') as log:
            writer = csv.DictWriter(log, fieldnames=[mac_address])
            # write the raw entry from accessing into a row
            writer.writerow(self.data)


def local_logging_loop():
    """Log `Globals.processed_data` to a csv file and then delete it from `Globals.processed_data`.
    
    Will be active if Basestation configuration flag `Settings.LOCAL_DATA_LOGGING` is set to `True`.

    """
    print("Start logging input_data to csv..")
    while True:
        # check if there is something to publish
        if not Globals.processed_data:
            sleep(Settings.PUBLISHING_DELAY)
        else:
            # locking the global dict while accessing it
            with Globals.processed_data_lock:
                # get processed_data
                local_data = Globals.processed_data
                # delete it because it is getting published
                Globals.processed_data = {}

            # log the available input_data
            Logger = LocalLogger(local_data, Settings.BACKUP_LOG_PATH)
            for macAddress in Logger.macAddresses:
                Logger.write_log(macAddress)


def raw_data_logging_loop():
    """Log raw input_data while simultaneously eiter publishing it to Thingsboard database or saving it locally.
    
    Will be active if Basestation configuration flag `Settings.SAVE_RAW_DATA` is set to `True`.
    
    Caution: The raw input_data logging functionality could log duplicate datapoints or produce other unforeseen
    mistakes.
    Process the resulting output before using it.

    """
    while True:
        # check if there is something to publish
        if not Globals.unprocessed_data:
            sleep(Settings.PUBLISHING_DELAY)
        else:
            # locking the global dict while accessing it
            with Globals.unprocessed_data_lock:
                # get processed_data
                local_data = Globals.unprocessed_data

            # publish the available input_data
            Logger = LocalLogger(local_data, Settings.RAW_LOG_PATH)
            for macAddress in Logger.macAddresses:
                Logger.write_log(macAddress)
        sleep(1)
