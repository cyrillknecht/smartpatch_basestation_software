"""
### Welcome to the SmartPatch Basestation Documentation

The Basestation Package contains all the functionality needed to run a SmartPatch Basestation. All major threads of
the main application have their own module. In order to adjust Basestation settings not configurable via the
Thingsboard UI, change them in `Settings.py`. All global variables used for this application are defined in
`Globals.py`. Please only access them using their matching thread_lock. """