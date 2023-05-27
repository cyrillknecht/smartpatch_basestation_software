# SmartPatch Basestation Software v1.0.0

[![Tests](https://github.com/cyrillknecht/smartpatch_basestation_software/actions/workflows/pytest.yml/badge.svg)](https://github.com/cyrillknecht/smartpatch_basestation_software/actions/workflows/pytest.yml)


## Quick overview
Run **run.py** on a Basestation device to connect to SmartPatches over BLE
and publish acquired data to a [Thingsboard](https://thingsboard.io/) server instance.  
Designed to be used with the 
[SmartPatch Connector App](https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/connector-app-v1).  
A part of the Smartpatch System.

## What is the SmartPatch System?
The SmartPatch System includes a SmartPatch for acquiring vital sensor data and a supporting ecosystem consisting of a 
[Basestation Software](https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/base-station-v1) 
designed to acquire the Sensor Data on a Basestation device (Raspberry Pi) and publishing it to a Thingsboard Server.
Further it includes a [Thingsboard](https://thingsboard.io/) server setup to display the acquired data and the 
[SmartPatch Connector App](https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/connector-app-v1) 
available for iOS and Android, that makes it easy to connect SmartPatches and assign them to a patient.

## Setup of the SmartPatch System

### Install Thingsboard Community Edition on your server

Thingsboard provides [Installation Guides](https://thingsboard.io/docs/user-guide/install/installation-options/)
for different types of servers.

After successfully installing your Thingsboard server, open its UI in a browser.
It can be found at http://basestation-ip-address:8080/.
If your Basestation device is a Raspberry Pi use the `ifconfig`command to obtain its IP address.

#### Set up the UI

In the Thingsboard UI:

1. Navigate to Dashboards
2. Select Add Dashboard/Import Dashboard
3. Add from this repository `AdditionalFunctionality/thingsboard_templates/smartpatch_dashboard.json`
4. Now select System Settings
5. As Home Dashboard choose *SmartPatch Dashboard* and uncheck *Hide home dashboard toolbar*.

Your SmartPatch UI is now set up and ready for use.

#### Provision Basestations (and Patients)

In the `AdditionalFunctionality` package you can find `Thingsboardsetup.py`,
a script that will help you provision Patients and Basestations to your Thingsboard Database.
Please only provision Patients using this script or with the 
[SmartPatch Connector App](https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/connector-app-v1).

In `ThingsboardSetup.py`, change `IP_ADDRESS` to your Thingsboard server IP address.
Change `PATIENT_FILE_PATH` and `BASESTATION_FILE_PATH` to your own lists of patients and Basestations.
Their format has to be like in the example files provided in the `thingsboard_templates`directory.

You can now run the modified `ThingsboardSetup.py` script to provision your devices and patients.

### Set up a Basestation

The Basestation Software was tested and is intended to be used on a Raspberry Pi 4B. It was tested on Raspbian Buster. 
For better BLE connections, an edimax BT-8500 BLE dongle was used.
Follow this guide to set up a Basestation for use:

1. Clone this repository on your Basestation device
 ```console
git clone https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/base-station-v1.git
 ```
3. Add all dependencies on your Basestation device

```console
cd base-station-v1
pip3 install -r requirements.txt
```

3. Change the `BROKER` property in `Basestation/Settings.py` your Thingsboard Servers IP Address/domain name. 
4. Adjust the `USERNAME` and `PASSWORD` properties in `Basestation/Settings.py` to your Thingsboard Servers tenant
password and username if you changed their default values.
5. Set `BASESTATION_NAME` to a Basestation name that you previously provided to Thingsboard
6. Execute run.py on your Basestation

```console
python3 run.py
```


If the application output includes:  

```console
Basestation 1 is activated and awaiting connections!
Access the data collected from this Basestation on the SmartPatch Data Visualization Platform:
http://your_thingsboard_server:8080
Change Patient-SmartPatch connections using the SmartPatch Connector App available on Android and iOs.
```

Congratulations, your Basestation is ready for test use!
If you do not want to run this Basestation permanently, you can skip to Connect SmartPatches.

#### Troubleshooting
There can be problems with the numpy installation. If these occur on Basestation startup, execute the following
commands:

```console
pip3 install --upgrade numpy
sudo apt-get install libatlas-base-dev
```

#### Run the Basestation Software permanently

To easily use SmartPatch Basestations, we want the Basestation Software to run automatically once a
Basestation has power. To achieve this you have to follow the steps listed below.

1. Open a terminal at your home directory on the Basestation.
2. Open the bash.rc file

```console
nano .bashrc
```
3. Add the following lines at the end of the file:

```console
sudo sh -c "/bin/echo 16 > /sys/kernel/debug/bluetooth/hci0/conn_min_interval"
sudo sh -c "/bin/echo 80 > /sys/kernel/debug/bluetooth/hci0/conn_max_interval"
sudo sh -c "/bin/echo 500 > /sys/kernel/debug/bluetooth/hci0/supervision_timeout"
cd base-station-v1
python3 run.py
```

4. Move back to your home directory

```console
cd /home/pi
```

5. Open/Create a desktop file in the autostart directory

```console
sudo nano /home/pi/.config/autostart/basestation.desktop 
```

6. Write the following lines in this file:

```shell
[Desktop Entry]
Encoding=UTF-8
Name=Basestation
Exec=lxterminal
Icon=lxterminal
Type=Application
Categories=Utility;
```

Now every time you restart your Basestation device should automatically open a terminal window and
run the Basestation Software in it.

**Caution: This will not work if the Basestation Software and the Thingsboard Server run on the same device.**

### Connect SmartPatches

To connect SmartPatches to your Basestation and Thingsboard Servers, please use the 
[SmartPatch Connector App](https://gitlab.ethz.ch/pbl/hs2021/flagship-smart-patch-2021/connector-app-v1).

## Further Documentation
You can find the package documentation in the [doc](/doc) directory of this repository.
Clone the repository and open `base-station-v1.html` to access it.




   

