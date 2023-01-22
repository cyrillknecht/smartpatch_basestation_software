"""
Implements the Ble thread used in `Basestation.py`.
Provides all functionality to receive data from multiple SmartPatches.

Implemented by Andreas Hunziker.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

import asyncio
import logging
import time

import bleak.exc
from bleak import BleakClient
from bleak import exc

# **********************************************************************************************************************
# ************* VALUES AND FUNCTIONS FOR TESTING THE GATEWAY ***********************************************************
# **********************************************************************************************************************

# SmartPatches: 'F6:E0:95:D5:9C:95', 'F0:4A:18:80:3E:E4', 'CD:BF:BE:48:BB:C5'

# dev boards:   'EE:60:5A:F4:AE:3B', 'FE:D6:C3:3B:FE:29', 'D4:6D:D4:BB:1E:A0', 'C0:70:A5:36:DA:1F',
#               'C4:87:FA:C7:A4:DE', 'FF:B8:2C:F7:1D:D8', 'F8:4E:59:1A:F4:72', 'E8:3C:B1:44:E1:65'

test_ble = False

if test_ble is True:
    import Globals
    import Settings
else:
    from Basestation import Globals, Settings

test_addresses = ['F6:E0:95:D5:9C:95', 'F0:4A:18:80:3E:E4']
imu = [i for i in range(120)]
ppg = [i + 10 for i in range(60)]
audio = [i for i in range(122)]
test_values = {'imu': imu, 'ppg': ppg, 'temperature': [37], 'audio': audio, 'voltage': 100, 'current': 2}


# simulation of user input
async def test_function():
    """Only useful while testing the gateway as standalone.
       Simulates user input.
        Args:
        Returns:
        """
    # init
    Globals.unprocessed_data = {}
    print("BLE test function started")
    # add device
    with Globals.mac_address_update_lock:
        for address in test_addresses:
            Globals.mac_address_update[address] = 'add'

    await asyncio.sleep(120)

    # remove device
    with Globals.mac_address_update_lock:
        for address in test_addresses:
            Globals.mac_address_update[address] = 'remove'

    # measure throughput
    throughput_test()


# throughput test
def throughput_test(test_val_arg=None):
    """Only useful while testing the gateway as standalone.
       Measure throughput of all devices which have sent input_data.
       Print the measured throughput for each device separately.
       Optional: Check if all received input_data is correct.
        Args:
            test_val_arg(dict, optional): a dictionary with the expected values for each characteristic
        Returns:
        """
    with Globals.unprocessed_data_lock:
        total_throughput = 0
        for address in Globals.unprocessed_data:
            error_cnt = 0
            bytes_cnt = 0
            start = Globals.unprocessed_data[address][0]['ts']
            end = Globals.unprocessed_data[address][-1]['ts']

            for datapoint in Globals.unprocessed_data[address]:
                for char, val in datapoint['values'].items():
                    bytes_cnt = bytes_cnt + len(val) * bytes_per_int[char]
                    if test_val_arg and val != test_val_arg[char]:
                        print(f"{char} received value: {val}\n expected value: {test_val_arg[char]}")
                        error_cnt = error_cnt + 1

            throughput = (bytes_cnt * 8 * (1000 / (end - start))) / 1000
            total_throughput = total_throughput + throughput
            print(f"{address}: {error_cnt} errors,"
                  f"received {bytes_cnt} bytes in {end - start} ms --> {throughput:.2f} kbit/s")
        print(f"total throughput: {total_throughput:.2f} kbit/s")


# **********************************************************************************************************************
# ********************* END OF GATEWAY TEST FUNCTIONS ******************************************************************
# **********************************************************************************************************************


# Handles of the characteristics
notify_handles = {2: 'imu', 6: 'ppg', 25: 'audio', 29: 'voltage', 32: 'current', 41: 'temperature'}
rw_handles = {'version': 36, 'config': 38}

# bytes per value
bytes_per_int = {'imu': 2, 'audio': 2, 'ppg': 4, 'temperature': 4, 'voltage': 4, 'current': 4}


# get the first key with the given value
def get_key_from_value(d, val):
    """Get a key with the given value from a dict.
       Useful for getting the mac addresses from the update dict.
        Args:
            d(dict): dictionary
            val: value
        Returns:
            key: key with the given value
        """
    keys = [k for k, v in d.items() if v == val]
    return keys[0]


# convert bytearray to int array
def convert_data(char, data):
    """Convert bytearray from notification to integer list.
        Args:
            char(str): characteristic which sent the notification
            data(bytearray): input_data to be converted
        Returns:
            list: list with the converted input_data
        """
    signed = False
    if (char == 'ppg') or (char == 'imu'):
        signed = True
    step = bytes_per_int[char]
    converted_data = [0] * int(len(data) / step)
    for index in range(len(converted_data)):
        if signed:
            converted_data[index] = int.from_bytes(bytes=data[step * index:step * (index + 1)], byteorder='little',
                                                   signed=True)
        else:
            converted_data[index] = int.from_bytes(bytes=data[step * index:step * (index + 1)], byteorder='little',
                                                   signed=False)
    return converted_data


# check if devices can be connected
async def search_connectable_devices():
    """Look for connection requests from the app.
        Args:
        Returns:
            str: mac address of the SmartPatch if a connection request is found, 'None' otherwise
        """
    with Globals.mac_address_update_lock:
        if 'add' in Globals.mac_address_update.values():
            address = get_key_from_value(d=Globals.mac_address_update, val='add')
            del Globals.mac_address_update[address]
            return address
        else:
            return 'None'


# check if device should be disconnected
async def search_remove_request(address):
    """Look for disconnection requests from the app.
       Every connected devices searches for its own disconnection request.
        Args:
            address(str): mac address of the device
        Returns:
            bool: True if a remove request is found, False otherwise
        """
    with Globals.mac_address_update_lock:
        if address in Globals.mac_address_update.keys():
            if Globals.mac_address_update[address] == 'remove':
                return True
            elif Globals.mac_address_update[address] == 'add':
                logging.exception(f"device with address {address} is already connected")
                del Globals.mac_address_update[address]
    return False


# disconnect from device
async def disconnect(device, address):
    """Disconnect from a device and stop all notifications.
        Args:
            device(bleak.backends.device.BLEDevice): device to be disconnected
            address(str): mac address of the device
        Returns:
        """
    # stop notifications
    for handle in notify_handles.keys():
        try:
            await device.stop_notify(char_specifier=handle)
        except (KeyError, exc.BleakError):
            logging.exception(f"{address} : {notify_handles[handle]} notifications could not be stopped")

    # disconnect
    try:
        await device.disconnect()
    except exc.BleakError:
        logging.exception(f"{address} unexpected disconnection")

    # delete remove request
    with Globals.mac_address_update_lock:
        del Globals.mac_address_update[address]
    print(f"Disconnected from SmartPatch with address {address}.")


# remove invalid remove requests
async def invalid_remove_request_task():
    """Thread searching for invalid remove requests.
       Handles remove requests for devices that are not connected.
        Args:
        Returns:
        """
    while True:
        await asyncio.sleep(30)
        with Globals.mac_address_update_lock:
            if 'remove' in Globals.mac_address_update.values():
                address = get_key_from_value(d=Globals.mac_address_update, val='remove')
                with Globals.connected_devices_lock:
                    if address not in Globals.connected_devices.keys():
                        logging.exception(f"invalid remove request from {address}")
                        del Globals.mac_address_update[address]


# get firmware version and add as connected device
async def add_connected(device, address):
    """Add device to the connected_devices dict in the form of 'mac address': firmware version.
        Args:
            device(bleak.backends.device.BLEDevice): device to be added
            address(str): mac address of the device
        Returns:
        """
    # get firmware version
    try:
        byte_array = await device.read_gatt_char(char_specifier=rw_handles['version'])
        firmware_version = byte_array.decode("utf-8")

        # add as connected
        with Globals.connected_devices_lock:
            Globals.connected_devices[address] = firmware_version

        print(f"Connected to SmartPatch with mac address {address} with firmware version {firmware_version}")

    except (KeyError, exc.BleakError):
        logging.exception(f"{address}: unable to read firmware version")


# change configuration of SmartPatch
async def search_config_update(device, address):
    """Check if the configuration should be changed and possibly send the new configuration to SmartPatch.
        Args:
            device(bleak.backends.device.BLEDevice): device to be updated
            address(str): mac address of the device

        """
    # check if there is a configuration update
    with Globals.config_update_lock:
        if Globals.smartpatch_config_update:
            new_config = Globals.smartpatch_config_update
        else:
            return

    # in case there is an update, send new configuration to SmartPatch
    config_bytes = new_config.to_bytes(length=1, byteorder='little')
    try:
        await device.write_gatt_char(char_specifier=rw_handles['config'], data=config_bytes, response=True)
    except exc.BleakError:
        logging.exception(f"{address}: unable to write configuration update")

    # wait for other devices to see the update before removing it
    await asyncio.sleep(30)
    with Globals.config_update_lock:
        Globals.smartpatch_config_update = 0


# get ready to connect to a device
async def connection_task():
    """Connection task, ready to connect to one SmartPatch.
       Connection and disconnection requests from the app are processed.

       If there is a connection request, the task tries to connect to the device with the given mac-address.
       Once connected, notifications are started and the received values are converted to integers and stored.
       If there is a remove request, the device gets disconnected and is ready to connect to another SmartPatch.

        """
    # address initialization
    address = 'None'

    # callback function
    def callback(sender, data):
        timestamp = round(time.time() * 1000)
        char = notify_handles[sender]
        converted_data = convert_data(char=char, data=data)
        with Globals.unprocessed_data_lock:
            if address not in Globals.unprocessed_data:
                Globals.unprocessed_data[address] = [{'ts': timestamp, 'values': {char: converted_data}}]
            else:
                Globals.unprocessed_data[address].append({'ts': timestamp, 'values': {char: converted_data}})

    # endless loop waiting for a change in the update dict
    while True:

        # check if devices can be connected
        address = await search_connectable_devices()

        # check if there is a valid device to connect
        if address != 'None':
            try:
                async with BleakClient(address, device="hci0", timeout=60.0) as device:
                    if device.is_connected:
                        await add_connected(device=device, address=address)

                    # start notifications
                    for handle in notify_handles.keys():
                        try:
                            await device.start_notify(handle, callback)
                        except (KeyError, exc.BleakError):
                            logging.exception(
                                f"{address} : {notify_handles[handle]} notifications could not be started")

                    # run until device needs to be removed
                    remove_request = False
                    while device.is_connected and remove_request is False:
                        await asyncio.sleep(1)
                        remove_request = await search_remove_request(address=address)
                        await search_config_update(device=device, address=address)

                    # disconnect from device
                    if device.is_connected:
                        await disconnect(device=device, address=address)

            # if there are many devices trying to connect simultaneously the traffic on the dbus can cause errors
            except exc.BleakDBusError:
                logging.exception(f"{address}: DBus Error, trying to connect again later")
                await asyncio.sleep(2)
                with Globals.mac_address_update_lock:
                    Globals.mac_address_update[address] = 'add'

            except (asyncio.TimeoutError, exc.BleakError):
                logging.exception(f"{address}: configuration error, device is not connectable")

            # reset address
            address = 'None'

        # wait a while before searching connectable devices again
        await asyncio.sleep(2)


async def ble_loop():
    """
       Main function for BLE thread.
       Starts 10 connection_tasks and one invalid_remove_request_task.
       All threads are endless loops and run concurrently.

    """
    if test_ble is True:
        await asyncio.gather(test_function(), invalid_remove_request_task(),
                             *(connection_task() for _ in range(Settings.DEVICE_MAXIMUM)))
    else:
        await asyncio.gather(invalid_remove_request_task(),
                             *(connection_task() for _ in range(Settings.DEVICE_MAXIMUM)))


if test_ble is True:
    asyncio.run(ble_loop())
