"""Script to simulate a real smart patch with random input_data that
    publishes sensor input_data to a predefined device on Thingsboard.

    Useful for testing a Thingsboard dashboard.

"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
import time
from random import randint
import paho.mqtt.client as paho


# generates random_integer between 0 and 100 every second
def generate_random_int(lower_bound=0, upper_bound=100):
    """Returns a random integer between two configurable bounds.
       Per default, it is between 0 and 100.

    Args:
      lower_bound(int, optional): lowest possible generated number. (Default value = 0)
      upper_bound(int, optional): highest possible generated number. (Default value = 100)

    Returns:
      int: random number between lower_bound and upper_bound

    """
    return randint(lower_bound, upper_bound)


# Access input_data for thingsboard server
ACCESS_TOKEN = 'AddYourOwnDeviceToken'  # Token of the Thingsboard device you want to publish to
BROKER = 'AddYourOwnIPAddress'  # host name
PORT = 1883


# main loop
def simulate(access_token, topic='v1/devices/me/telemetry', publishing_frequency=1,
             broker=BROKER, port=PORT):
    """Publish simulated Smartpatch Data to Thingsboard database.
    
    Publish a datapoint consisting of several random values assigned to keys to the device chosen with the access_token.

    Args:
      access_token(str): token of Thingsboard device which is selected for publishing
      topic(str, optional): MQTT topic to publish to (Default value = 'v1/devices/me/telemetry')
      publishing_frequency(int, optional): frequency of publishing datapoints (Default value = 1)
      broker(str, optional): thingsboard server IP address (Default value = Settings.BROKER)
      port(str, optional): port to publish input_data (Default value = Settings.PORT)

    """
    print(f"Starting SmartPatch Simulator with connected Patient:\n{access_token}")
    while True:
        # dict with random sensor input_data
        random_data = {'heartrate': generate_random_int(40, 200), 'bloodOxygenation': generate_random_int(20, 100),
                       'respirationRate': generate_random_int(),
                       'temperature': generate_random_int(1, 40), 'activityLevel': generate_random_int(1, 5),
                       'batteryPercentage': generate_random_int(), 'firmwareVersion': '1.0.0'}

        # initializing mqtt client

        client = paho.Client()  # create client object
        client.username_pw_set(access_token)  # access token from Thingsboard device
        client.connect(broker, port, keepalive=60)  # establish connection

        # publishing to Thingsboard server
        response = client.publish(topic, str(random_data))
        response.wait_for_publish()

        # wait before next publish
        time.sleep(1/publishing_frequency)


# run script
if __name__ == '__main__':
    simulate("Patient 1", broker='192.168.0.235')
