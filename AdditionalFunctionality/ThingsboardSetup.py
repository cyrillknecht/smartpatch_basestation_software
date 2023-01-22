"""
Script to automate providing a Thingsboard server with patients and Basestations.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import Basestation modules
from AdditionalFunctionality import ThingsboardApiTools

# Thingsboard Server IP address
IP_ADDRESS = "YourThingsboardServerIpAddress"

# Paths to fetch Data from
PATIENT_FILE_PATH = 'Setup_Data/patients.csv'
BASESTATION_FILE_PATH = 'Setup_Data/example_basestations.csv'


def thingsboard_initial_setup(basestation_file_path=BASESTATION_FILE_PATH
                              , patient_file_path=PATIENT_FILE_PATH):
    """Provision patients and Basestations from csv files to Thingsboard database.
    
       Should be run only once with the same files, otherwise it will result in an error.

    Args:
      basestation_file_path(str, optional): path to csv that contains basestations (ends with your_file.csv)
                                            (Default value = BASESTATION_FILE_PATH)
      patient_file_path(str, optional): path to csv that contains patients (ends with your_file.csv)
                                        (Default value = PATIENT_FILE_PATH)

    """

    # start tool with default values
    tool = ThingsboardApiTools.ApiTools(api_url='http://' + IP_ADDRESS + ':8080')

    # add basestation devices
    tool.add_entity_csv(file_path=basestation_file_path, entity_type='Basestation')

    # add patients from list initial patients list
    tool.add_entity_csv(file_path=patient_file_path, entity_type='Patient')
    # add second device for raw data logging for every patient
    tool.add_entity_csv(file_path=patient_file_path, entity_type='Raw')


# run script
if __name__ == '__main__':
    thingsboard_initial_setup()
