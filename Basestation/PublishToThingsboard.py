"""
    Module for publishing sensor input_data to a Thingsboard server using MQTT.

    Data should be in the following format for publishing:

    input_data = {"accesstoken":
    [{"ts": timestamp_in_ms, "values":{"my_attribute_1": attribute_value, "my_attribute2": my_attribute_2_values}},
    {"ts": other_timestamp_in_ms, "values":{"my_attribute_1": attribute_value, "my_attribute2": my_attribute_2_value}}
    ]}


    Further Breakdown of input_data structure:

    input_data = {"accesstoken": list_of_datapoints}

    accesstoken is a Thingsboard device accesstoken.

    For the current system architecture the accesstoken is the name of the selected patient.

    *Caution: Do not forget to wrap the accesstoken in double quotation marks.*


    datapoint = {"ts": timestamp_in_ms, "values": dict_of_values} OR dict_of_values

    dict_of_values = {"my_attribute_1": attribute_value, "my_attribute2": my_attribute_2_value}
    There is no limitation to the number of key-value-pairs.

"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
import logging
from time import sleep
import paho.mqtt.client as paho
from tb_rest_client.rest import ApiException

# import Basestation modules
from Basestation import Mapping, Globals, Settings


class DataLogger:
    """Create a Logger that can publish telemetry or attributes to a Thingsboard server,
    if input_data comes in the form specified in the module description.
    """
    access_token: str
    """Thingsboard access token for current patient."""

    data: list
    """Special dict structure for datapoints, see module description."""

    broker: str
    """IP address of Thingsboard server."""

    port: str
    """Data transfer port of Thingsboard Server."""

    def __init__(self, input_data, broker=Settings.BROKER, port=Settings.PORT):
        """Initialize a DataLogger with given data in the right format.
        For data format see module description.

        Args:
            input_data(dict): special dict structure for datapoints, see module description
            broker(str): IP address of Thingsboard server
            port(str): data transfer port of Thingsboard Server

         """
        self.access_token = list(input_data.keys())[0]
        self.broker = broker
        self.port = port
        self.data = list(input_data.values())[0]

        # initializing mqtt client
        self.client = paho.Client()  # create client object
        self.client.username_pw_set(self.access_token)  # access token from thingsboard device
        self.client.connect(self.broker, self.port, keepalive=60)  # establish connection

    def publish(self, publish_address):
        """Publish input_data to publish_adress on Thingsboard server.

        Args:
          publish_address(str): mqtt topic to publish to

        """
        for datapoint in self.data:
            response = self.client.publish(publish_address, str(datapoint))
            sleep(0.002)  # small delay for
            response.wait_for_publish()  # blocks until  the message is delivered.

    def publish_telemetry(self):
        """Publish telemetry input_data to thingsboard server."""
        self.publish(publish_address='v1/devices/me/telemetry')

    def publish_attribute(self):
        """Publish attributes to thingsboard server."""
        self.publish(publish_address='v1/devices/me/attributes')


def publishing_loop():
    """Publish input_data obtained from global dict processed_data to according patient on thingsboard server,
       and delete input_data that was published from said dict.
    
       Main function for `Publishing` thread.
       In order to adjust the publishing frequency adjust `Settings.PUBLISHING_DELAY`.
       Make sure it is not slower than the `DataProcessing` Output, otherwise the application will eventually crash.

    """
    print("Started publishing data to Thingsboard server.")
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
            try:
                # publish the available input_data
                for macAddress in local_data:
                    # get the patient accesstoken
                    accesstoken = Mapping.get_matching_device(macAddress,
                                                              current_device_mapping=Globals.patient_mapping)
                    # rebuild the input_data
                    if accesstoken:  # checking if an accesstoken was found for the current mac-address
                        assigned_data = {accesstoken: local_data[macAddress]}
                        # locking the global dict while accessing it
                        with Globals.connected_devices_lock:
                            # add a firmware version to input_data if there is one
                            if macAddress in Globals.connected_devices:
                                assigned_data[accesstoken].append(
                                    {"firmwareVersion": Globals.connected_devices[macAddress]})

                        # publish the input_data
                        logger = DataLogger(input_data=assigned_data)
                        logger.publish_telemetry()

            except ApiException as exception:
                logging.exception(exception)


def raw_data_publishing_loop():
    """Publish input_data obtained from global dict `Globals.unprocessed_data` to according patient on thingsboard
    server.

       Main function for `RawPublishing` thread.
       In order to adjust the publishing frequency adjust `Settings.PUBLISHING_DELAY`.
       Make sure it is not faster than the `DataProcessing` Output, otherwise the application will eventually crash.

       Warnings:
           Test Version, can lead to duplicates in database.

    """
    print("Started publishing raw data to Thingsboard server.")
    while True:
        # check if there is something to publish
        if not Globals.unprocessed_data:
            sleep(Settings.PUBLISHING_DELAY)
        else:
            # locking the global dict while accessing it
            with Globals.unprocessed_data_lock:
                # get processed_data
                local_data = Globals.unprocessed_data
            try:
                # publish the available input_data
                for macAddress in local_data:
                    # get the patient accesstoken
                    accesstoken = Mapping.get_matching_device(macAddress,
                                                              current_device_mapping=Globals.patient_mapping)
                    # rebuild the input_data
                    if accesstoken:  # checking if an accesstoken was found for the current mac-address
                        # choosing the raw input_data device to publish the raw input_data to
                        assigned_data = {accesstoken + " Raw Data": local_data[macAddress]}
                        # publish the input_data
                        logger = DataLogger(input_data=assigned_data)
                        logger.publish_telemetry()
            except ApiException as exception:
                logging.exception(exception)
            sleep(1)
