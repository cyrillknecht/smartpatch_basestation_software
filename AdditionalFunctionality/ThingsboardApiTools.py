"""
Helper Functions that use the Thingsboard API.

Mainly used in ThingsboardSetup.py.
Further methods are implemented, for example methods to get telemetry input_data for patient.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
import logging
import numpy as np
from tb_rest_client.rest import ApiException
from tb_rest_client.rest_client_ce import *

# logging configuration
logging.basicConfig(level=logging.DEBUG)


class ApiTools:
    """Tool to interact with the Thingsboard API."""

    api_url: str
    """Url of chosen thingsboard server:"""

    username: str
    """Username on chosen thingsboard server."""

    password: str
    """""Password on chosen thingsboard server."""

    def __init__(self, api_url, username='tenant@thingsboard.org', password='tenant'):
        """
        Initiate tool with the parameters to access the Thingsboard API.

        Args:
            api_url(str, optional): url of chosen thingsboard server
            username(str, optional): username on chosen thingsboard server (Default value = 'tenant@thingsboard.org')
            password(str, optional): password on chosen thingsboard server (Default value = 'tenant')

        """
        self.username = username
        self.password = password
        self.url = api_url

    # login to REST API
    def login(self):
        """Log into Thingsboard api."""
        # Creating the REST client object with context manager to get auto token refresh
        with RestClientCE(base_url=self.url) as rest_client:
            try:
                # Auth with credentials
                rest_client.login(username=self.username, password=self.password)
            except ApiException as e:
                logging.exception(e)

    def add_device(self, device_name, device_type):
        """Add a new device with device_name from entity_type to the Thingsboard database.

        Args:
          device_name(str): name of device in Thingsboard database
          device_type(str): type of device in Thingsboard database

        """
        with RestClientCE(base_url=self.url) as rest_client:
            try:
                # Auth with credentials
                rest_client.login(username=self.username, password=self.password)
                # Creating Device
                new_device = Device(name=device_name, type=device_type)
                rest_client.save_device(new_device)
            except ApiException as e:
                logging.exception(e)

    def add_asset(self, asset_name, asset_type):
        """Add a new asset with asset_name from asset_type to the Thingsboard database.

        Args:
          asset_name(str): name of asset in Thingsboard database
          asset_type(str): type of asset in Thingsboard database

        """
        with RestClientCE(base_url=self.url) as rest_client:
            try:
                # Auth with credentials
                rest_client.login(username=self.username, password=self.password)
                # Creating Asset
                new_asset = Asset(name=asset_name, type=asset_type)
                rest_client.save_asset(new_asset)
            except ApiException as e:
                logging.exception(e)

    def add_customer(self, customer_name, customer_title):
        """Add a new customer with customer_name and customer_title to the Thingsboard database.

        Args:
          customer_name(str): name of customer in Thingsboard database
          customer_title(st): title of customer in Thingsboard database

        """
        with RestClientCE(base_url=self.url) as rest_client:
            try:
                # Auth with credentials
                rest_client.login(username=self.username, password=self.password)
                # Creating Customer
                new_customer = Customer(name=customer_name, title=customer_title)
                rest_client.save_customer(new_customer)
            except ApiException as e:
                logging.exception(e)

    def add_entity_list(self, entity_list, device_type):
        """Add entities provided in entity_list to Thingsboard database.

        Args:
          entity_list(list: list): list of names of all entities that will be added
          device_type(str): type of entities that will be added.

        """

        with RestClientCE(self.url) as rest_client:
            try:

                rest_client.login(self.username, self.password)
                for entity_name in entity_list:
                    entity = Device(name=entity_name, type=device_type)
                    rest_client.save_device(entity, access_token=entity_name)

            except ApiException as e:
                logging.exception(e)

    def add_entity_csv(self, file_path, entity_type, chosen_delimiter=';'):
        """Add a list of entities from a csv file to Thingsboard database.
        
        Obtain a list of entity names from csv at file_path that uses chosen_delimiter.
        The obtained entities are then added to the Thingsboard database.

        Args:
          file_path(str): path to csv (ends with /your_file.csv)
          entity_type(str): type of provisioned entities
          chosen_delimiter(str, optional): delimiter of used csv file (Default value = ';')

        """

        file_reader = np.loadtxt(file_path, dtype='str', delimiter=chosen_delimiter)
        entity_list = list(file_reader)

        if entity_type == 'Raw':
            entity_list = [entity + ' Raw Data' for entity in entity_list]

        self.add_entity_list(entity_list=entity_list, device_type=entity_type)

    def get_device_id_dict(self, max_devices=100):
        """Return a dict with device names as keys and Thingsboard device ids as values.
        
        Fetch up to max_devices with type Patient from Thingsboard database. For every Patient
        the Thingsboard device id is added as value. This id can be used to access the Thingsboard
        device with their API.

        Args:
          max_devices(int, optional): maximum number of devices that will be fetched (Default value = 100)

        Returns:
          dict: dict with device names as keys and device ids as values:

        """
        device_id_dict = {}
        with RestClientCE(self.url) as rest_client:
            try:
                rest_client.login(self.username, self.password)
                message = rest_client.get_tenant_device_infos(page_size=str(max_devices), page='0',
                                                              type='Patient')
                for current_device in message.data:
                    device_id_dict[current_device.name] = current_device.id.id

            except ApiException as e:
                logging.exception(e)
        return device_id_dict

    def get_device_id(self, device_name):
        """Return a Thingsboard device id for given device_name.

        Args:
          device_name: name of queried device (equal to name of patient if the device_type is patient)

        Returns:
          str: the Thingsboard device id

        """
        device_id_dict = self.get_device_id_dict()
        if device_name in device_id_dict:
            return device_id_dict[device_name]
        else:
            return f'{device_name} is not in database. '

    # noinspection PyTypeChecker
    def get_telemetry(self, thingsboard_device_id, key, start_ts_ms, end_ts_ms):
        """Return telemetry input_data as array of input_data points for given device in between start_ts_ms and
           end_ts_ms.
        
        The timestamps for Thingsboard have to be in milliseconds.
        That is not the usual way python provides timestamps.
        To get start_ts_ms and end_ts_ms you can use get get_ts_ms to convert a default time.time() timestamp.

        Args:
          thingsboard_device_id(str): id for device from Thingsboard database
          key(str): telemetry key from Thingsboard database that is accessed
          start_ts_ms(int): fetch telemetry input_data after this timestamp
          end_ts_ms(int): fetch telemetry input_data up to this timestamp

        """
        with RestClientCE(self.url) as rest_client:
            try:
                rest_client.login(self.username, self.password)
                data = rest_client.get_timeseries(entity_type='DEVICE',
                                                  entity_id=thingsboard_device_id,
                                                  keys=key,
                                                  start_ts=str(start_ts_ms),
                                                  end_ts=str(end_ts_ms))
                if data:
                    return data[key]
                else:
                    return 'No input_data found'

            except ApiException as e:
                logging.exception(e)

    @staticmethod
    def get_ts_ms(timestamp):
        """Returns a Thingsboard-compatible timestamp in milliseconds.

        Args:
          timestamp(int): a standard timestamp in seconds

        Returns:
          int: rounded timestamp in milliseconds

        """
        milliseconds = int(round(timestamp * 1000))
        return milliseconds

    def update_home_dashboard(self, home_dashboard_id):
        """Sets the Thingsboard servers home dashboard to the dashboard with home_dashboard_id.

        Args:
          home_dashboard_id(DashboardId): object, only accessible via the Thingsboard API

        """
        with RestClientCE(self.url) as rest_client:
            try:
                rest_client.login(self.username, self.password)
                rest_client.set_tenant_home_dashboard_info(body=HomeDashboardInfo(home_dashboard_id,
                                                                                  hide_dashboard_toolbar=False))

            except ApiException as e:
                logging.exception(e)
