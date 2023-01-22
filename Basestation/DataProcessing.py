"""
Implementation of input_data processing algorithms.

Take data from global dict `Globals.unprocessed_data` , process it and append it to `Globals.processed_data`.

Output to `Globals.processed_data should be in the following format:

input_data = {"current_smartpatch_mac_address": [{"ts": timestamp_in_ms, "values":{"firmwareVersion":
currentFirmwareVersion, "batteryPercentage": currentBatteryPercentage, "temperature": currentTemperature,
"heartrate": currentHeartrate, "respirationRate": currentRespirationRate, "bloodOxygenation": currentOxygenation,
"activityLevel": currentActivityLevel }},... ]}


Further Breakdown of input_data structure:

input_data = {"accesstoken": list_of_datapoints}

accesstoken is a Thingsboard device accesstoken.

For the current system architecture the accesstoken is the name of the selected patient.

*Caution: Do not forget to wrap the accesstoken in double quotation marks.*


datapoint = {"ts": timestamp_in_ms, "values": dict_of_values} OR dict_of_values

dict_of_values = {"my_attribute_1": attribute_value,.., "my_attribute_x": my_attribute_x_value}

There is no limitation to the number of key-value-pairs. All attribute keys should be written in **camelCase**.
Not all keys-value pairs have to be in every input_data point.
"""

# setting the docstring format for the documentation
__docformat__ = 'google'

# import libraries
import time
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import butter, filtfilt
from matplotlib import pyplot as plt
import heartpy as hp
import asyncio
import logging
from tqdm import tqdm
import warnings


# import Basestation modules
from Basestation import Globals, Settings

# do not print numpy warnings
warnings.filterwarnings('ignore')

# data processing variables
duration = {}
current_ts = {}
local_data = {}
local_imu_raw = {}
local_imu_converted = {}
local_ppg = {}
local_temp = {}
local_voltage = {}
local_activity_level = {}
local_battery_percentage = {}

local_HR = {}
local_SPO2 = {}

# handles for live plots
ppg_plot = []
hr_filtered_plot = []
rr_filtered_plot = []
hr_plot = []
spo2_plot = []
temp_plot = []

# heartpy dicts
hp_HR = {}
hp_RMSSD = {}
hp_RR = {}

# definitions for ppg signal analysis
SAMPLING_FREQUENCY = 100
SAMPLE_DURATION = 20  # Samples are 10s each
SAMPLE_LENGTH = SAMPLING_FREQUENCY * SAMPLE_DURATION
SAMPLING_PERIOD = 1.0 / SAMPLING_FREQUENCY
x = np.linspace(0.0, SAMPLING_PERIOD * SAMPLE_LENGTH, SAMPLE_LENGTH, endpoint=False)
xf = fftfreq(SAMPLE_LENGTH, SAMPLING_PERIOD)[:SAMPLE_LENGTH // 2]

# coefficients for blood oxygen level estimation
a_coeff = 1.5958422
b_coeff = -34.6596622
c_coeff = 112.6898759


def delete_old_data(address):
    """ Delete old data stored in local variables if it exceeds the amount needed for processing and plotting.
    Args:
        address(str): MAC address of the Smartpatch
    """
    global local_ppg, local_temp, local_imu_raw, local_voltage, local_activity_level, local_imu_converted, \
        local_HR, local_SPO2

    if len(local_ppg[address]) > 5000:
        local_ppg[address] = local_ppg[address][4000:]
    if len(local_imu_raw[address]) > 2000:
        local_imu_raw[address] = local_imu_raw[address][1000:]
    if len(local_temp[address]) > 200:
        local_temp[address] = local_temp[address][100:]
    if address in local_voltage:
        if len(local_voltage[address]) > 200:
            local_voltage[address] = local_voltage[address][100:]
    if len(local_activity_level[address]) > 200:
        local_activity_level[address] = local_activity_level[address][100:]
    if len(local_imu_converted[address]) > 2000:
        local_imu_converted[address] = local_imu_converted[address][1000:]
    if len(local_HR[address]) > 200:
        local_HR[address] = local_HR[address][100:]
    if len(local_SPO2[address]) > 200:
        local_SPO2[address] = local_SPO2[address][100:]


def split_data(address):
    """ Separate unprocessed data for further processing.
    Args:
        address(str): MAC address of the Smartpatch
    """
    global local_data, local_ppg, local_temp, local_imu_raw, local_voltage
    for datapoint in local_data:
        for char, val in datapoint['values'].items():

            if char == 'ppg':
                if address not in local_ppg:
                    local_ppg[address] = np.reshape(val, (-1, 3))
                else:
                    local_ppg[address] = np.append(local_ppg[address], np.reshape(val, (-1, 3)), 0)

            elif char == 'imu':
                if address not in local_imu_raw:
                    local_imu_raw[address] = np.reshape(val, (-1, 6))
                else:
                    local_imu_raw[address] = np.append(local_imu_raw[address], np.reshape(val, (-1, 6)), 0)

            elif char == 'temperature':
                if address not in local_temp:
                    local_temp[address] = [val[0] / 200.0]
                else:
                    local_temp[address].append(val[0] / 200.0)

            elif char == 'voltage':
                if address not in local_voltage:
                    local_voltage[address] = [val[0]]
                else:
                    local_voltage[address].append(val[0])
            else:
                print("unknown datatype received")
    local_data = {}


def write_back(address):
    """ Write calculated/measured data to Globals.processed_data.
    Args:
        address(str): MAC address of the Smartpatch
    """
    global local_voltage, local_imu_converted, local_HR, local_SPO2, local_temp, local_activity_level, \
        current_ts, hp_RR
    if address in local_battery_percentage:
        battery_percentage = local_battery_percentage[address]
    else:
        battery_percentage = 100

    sp_data = {"ts": current_ts[address], "values": {"firmwareVersion": 1.23,
                                                     "batteryPercentage": battery_percentage,
                                                     "temperature": local_temp[address][-1],
                                                     "heartrate": local_HR[address][-1], "respirationRate":
                                                         hp_RR[address][-1],
                                                     "bloodOxygenation": local_SPO2[address][-1],
                                                     "activityLevel": local_activity_level[address][-1]}}
    with Globals.processed_data_lock:
        if address not in Globals.processed_data:
            Globals.processed_data[address] = [sp_data]
        else:
            Globals.processed_data[address].append(sp_data)


plt.style.use('ggplot')


def live_plotter(address, line1, line2, line3, line4, line5, line6, pause_time=0.1):
    """ Implements live plots, adjusted from https://github.com/makerportal/pylive.
    Only for Debugging.
    Args:
        address(str): MAC address of the Smartpatch
        line1: Handle for subplot 1
        line2: Handle for subplot 2
        line3: Handle for subplot 3
        line4: Handle for subplot 4
        line5: Handle for subplot 5
        line6: Handle for subplot 6
        pause_time: timeout for matplotlib to catch up
    Returns:
        line1: Handle for subplot 1
        line2: Handle for subplot 2
        line3: Handle for subplot 3
        line4: Handle for subplot 4
        line5: Handle for subplot 5
        line6: Handle for subplot 6
    """
    global local_ppg, local_SPO2, local_HR, local_temp

    b, a = butter(3, [0.7, 3.5], 'band', fs=100)
    b2, a2 = butter(3, [0.05, 3.5], 'band', fs=100)

    if not line1:
        plt.ion()
        fig = plt.figure(figsize=(20, 12))
        ax = fig.add_subplot(321)
        ax2 = fig.add_subplot(323)
        ax3 = fig.add_subplot(325)
        ax4 = fig.add_subplot(322)
        ax5 = fig.add_subplot(324)
        ax6 = fig.add_subplot(326)

        line1, = ax.plot(np.arange(0, 800, 1), local_ppg[address][-800:, 2], alpha=0.8)
        line2, = ax2.plot(np.arange(0, 800, 1), filtfilt(b, a, local_ppg[address][-800:, 2]), alpha=0.8)
        line3, = ax3.plot(np.arange(0, 800, 1), filtfilt(b2, a2, local_ppg[address][-800:, 2]), alpha=0.8)
        line4, = ax4.plot(np.arange(0, 60, 1), local_HR[address][-60:], alpha=0.8)
        line5, = ax5.plot(np.arange(0, 60, 1), local_SPO2[address][-60:], alpha=0.8)
        line6, = ax6.plot(np.arange(0, 60, 1), local_temp[address][-60:], alpha=0.8)

        ax.set_title("Green PPG channel")
        ax2.set_title("Green PPG channel, filtered for heartrate")
        ax3.set_title("Green PPG channel, filtered for hr & rr")
        ax4.set_title("Heart Rate, 60s")
        ax5.set_title("SPO2, 60s")
        ax6.set_title("Temperature, 60s")

        plt.show()

    line1.set_ydata(local_ppg[address][-800:, 2])
    line2.set_ydata(filtfilt(b, a, local_ppg[address][-800:, 2]))
    line3.set_ydata(filtfilt(b2, a2, local_ppg[address][-800:, 2]))
    line4.set_ydata(local_HR[address][-60:])
    line5.set_ydata(local_SPO2[address][-60:])
    line6.set_ydata(local_temp[address][-60:])

    for ax in plt.gcf().get_axes():
        ax.relim()
        ax.autoscale_view()
    plt.pause(pause_time)

    return line1, line2, line3, line4, line5, line6


def plots(address):
    """ Generates live plots of raw PPG signal, filtered PPG signal, Heart Rate, SPO2 and Temperature.
    Only for Debugging.
    Args:
        address: MAC address of the Smartpatch

    """
    global ppg_plot, hr_filtered_plot, rr_filtered_plot, hr_plot, spo2_plot, temp_plot

    ppg_plot, hr_filtered_plot, rr_filtered_plot, hr_plot, spo2_plot, temp_plot = live_plotter(address \
                                                                                               , ppg_plot,
                                                                                               hr_filtered_plot,
                                                                                               rr_filtered_plot,
                                                                                               hr_plot, spo2_plot,
                                                                                               temp_plot)
    return


def print_values(address):
    """ Prints measured/calculated values
    Only for Debugging
    Args:
        address: MAC address of the Smartpatch
    """
    global local_voltage, local_imu_converted, local_HR, local_SPO2, local_temp, local_ppg, \
        local_battery_percentage, local_activity_level

    xmx = max(local_imu_converted[address][-120:, 3])
    xmy = max(local_imu_converted[address][-120:, 4])
    xmz = max(local_imu_converted[address][-120:, 5])

    print('----------------------------' + str(address) + '--------------------------------')
    # fix for missing voltage service
    if address in local_voltage:
        print('voltage level: ' + str(local_voltage[address][-1]) + 'mV | Battery life : '
              + str(local_battery_percentage[address]) + '%')
    print('max acceleration: x:' + str(xmx) + ' y: ' + str(xmy) + ' z ' + str(xmz))
    print('Heart Rate: (own)' + str(local_HR[address][-1]) + '   (heartpy:)' + str(hp_HR[address][-1]))
    print('Blood Oxygenation: ' + str(local_SPO2[address][-1]))
    print('Respiration Rate: ' + str(hp_RR[address][-1]))
    print('Body Skin Temperature: ' + str(local_temp[address][-1]))
    print('Activity:' + str(local_activity_level[address][-1]))


def imu_conversion(address):
    """ Implements conversion of raw IMU data into deg*s^-1 and m*s^-2 and detects activity.
    Args:
        address: MAC address of the Smartpatch
    """
    global local_imu_raw, local_imu_converted, local_activity_level

    # Convert data into deg*s^-1 and m*s^-2 (multiply sensitivity at full scale and raw value)
    a = np.array([[0.0175, 0.0175, 0.0175, 0.000598, 0.000598, 0.000598]])
    conversion_matrix = np.diag(a[0])
    local_imu_converted[address] = np.matmul(local_imu_raw[address], conversion_matrix)

    xmx = max(local_imu_converted[address][-120:, 3])
    xmy = max(local_imu_converted[address][-120:, 4])
    xmz = max(local_imu_converted[address][-120:, 5])
    abs_xl = np.zeros(120)
    activity = 0
    for i in range(120):
        abs_xl[i] = np.sqrt(local_imu_converted[address][-i, 3] ** 2 + local_imu_converted[address][-i, 4] ** 2 + \
                            local_imu_converted[address][-i, 5] ** 2)
    if max(abs_xl) > 12.0:
        activity = 1

    if address not in local_activity_level:
        local_activity_level[address] = [activity]
    else:
        local_activity_level[address].append(activity)


def ppg_analysis(address):
    """ Estimates heart rate and blood oxygen levels from raw PPG signal.
    Args:
        address: MAC address of the Smartpatch
    """
    global local_ppg, a_coeff, b_coeff, c_coeff, x, xf, SAMPLE_LENGTH, SAMPLE_DURATION, SAMPLING_PERIOD, \
        SAMPLING_FREQUENCY, local_HR, local_SPO2

    # The PPG channels are filtered between 0.7 Hz and 3.5 Hz (42 to 210 BPM) in order to extract the heart rate
    b, a = butter(3, [0.7, 3.5], 'band', fs=100)
    filtered_red = filtfilt(b, a, local_ppg[address][-SAMPLE_LENGTH:, 0])
    filtered_ir = filtfilt(b, a, local_ppg[address][-SAMPLE_LENGTH:, 1])
    filtered_green = filtfilt(b, a, local_ppg[address][-SAMPLE_LENGTH:, 2])

    # Perform a Fast Fourier Transform to determine heart rate
    y = filtered_green
    yf = fft(y)
    plot_start = int(0.75 * SAMPLE_DURATION)  # between 45 BPM and 210 BPM
    plot_stop = int(3.5 * SAMPLE_DURATION)
    a = np.abs(yf[plot_start:plot_stop])  # extract the dominant frequency component
    hr_index = np.argmax(a) + plot_start
    if address not in local_HR:  # store the calculated value
        local_HR[address] = [round(60 * xf[hr_index])]
    else:
        local_HR[address].append(round(60 * xf[hr_index]))

    # Determine AC and DC components of the red and IR channels of the PPG signal
    ac_red = np.abs(fft(filtered_red))[hr_index]  # The AC component is extracted at the heartrate
    ac_ir = np.abs(fft(filtered_ir))[hr_index]
    dc_red = sum(local_ppg[address][-SAMPLE_LENGTH:, 0]) / SAMPLE_LENGTH
    dc_ir = sum(local_ppg[address][-SAMPLE_LENGTH:, 1]) / SAMPLE_LENGTH

    # Calculation based on https://www.maximintegrated.com/en/design/technical-documents/app-notes/6/6845.html
    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    SPO2 = round(a_coeff * (R ** 2) + b_coeff * R + c_coeff)
    if SPO2 > 100:
        SPO2 = 100
    if address not in local_SPO2:  # store the calculated value
        local_SPO2[address] = [SPO2]
    else:
        local_SPO2[address].append(SPO2)


def heartpy_analysis(address):
    """ PPG signal is analyzed by heartpy. Estimates heart rate and respiration rate and calculates RMSSD.
    Args:
        address: MAC address of the Smartpatch
    """
    global hp_HR, hp_RR, hp_RMSSD
    # The filter is chosen such that both the respiration rate and the heartrate retained
    filtered = hp.filter_signal(local_ppg[address][-2000:, 2], [0.05, 3.5], sample_rate=100.0, order=3,
                                filtertype='bandpass')

    working_data, measures = hp.process(filtered, sample_rate=100.0, report_time=False)

    if address not in hp_HR:
        hp_HR[address] = [measures['bpm']]  # store BPM value
    else:
        hp_HR[address].append(measures['bpm'])

    if address not in hp_RMSSD:
        hp_RMSSD[address] = [measures['rmssd']]  # store RMSSD
    else:
        hp_RMSSD[address].append(measures['rmssd'])

    if address not in hp_RR:
        hp_RR[address] = [measures['breathingrate']]  # store respiration rate
    else:
        hp_RR[address].append(measures['breathingrate'])


def calc_battery_percentage(address):
    """ Estimates battery life based on voltage. Assumes that 7/8 of the total charge is used between 4.15v and 3.65v.
        -> TODO: actual discharge curve needs to be measured with final battery
    Args:
        address: MAC address of the Smartpatch

    """
    global local_voltage, local_battery_percentage
    # fix for missing voltage service
    if address in local_voltage:
        voltage = local_voltage[address][-1]
        if voltage > 3650:
            local_battery_percentage[address] = 12 + 0.176 * (voltage - 3650)
        else:
            local_battery_percentage[address] = 0.0342 * (voltage - 3650)


async def data_processing():
    """ Executes data processing routine on new data received from all Smartpatches.
    """
    # i = 1

    # wait until enough data has accumulated
    print("Waiting for enough data to start processing..")
    for _ in tqdm(range(30), leave=False):
        await asyncio.sleep(1)

    while True:
        # check if there is input_data to fetch
        if Globals.unprocessed_data:
            # take input_data out of unprocessed_data
            with Globals.unprocessed_data_lock:
                global local_data, duration, current_ts
                for address in Globals.unprocessed_data:
                    start = Globals.unprocessed_data[address][0]['ts']
                    end = Globals.unprocessed_data[address][-1]['ts']
                    duration[address] = end - start
                    current_ts[address] = end
                    local_data = Globals.unprocessed_data[address]
                    try:
                        split_data(address)
                        ppg_analysis(address)
                        imu_conversion(address)
                        calc_battery_percentage(address)
                        heartpy_analysis(address)
                        write_back(address)
                        delete_old_data(address)
                    except (KeyError, hp.exceptions.BadSignalWarning) as e:
                        logging.exception(f"{address} {e}")

                    # if i > 60:
                    #    plots(address)
                Globals.unprocessed_data = {}
        await asyncio.sleep(1)
        # i += 1


def no_data_processing():
    """Unprocessed input_data gets directly passed to processed_data.

    """
    while True:
        # check if there is input_data to fetch
        if Globals.unprocessed_data:
            # take input_data out of unprocessed_data
            with Globals.unprocessed_data_lock:
                current_data = Globals.unprocessed_data
                Globals.unprocessed_data = {}

            # save it into processed_data
            with Globals.processed_data_lock:
                Globals.processed_data = current_data

        time.sleep(Settings.PROCESSING_DELAY)
