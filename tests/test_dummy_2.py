import Basestation.Globals as Globals


def test_globals_patient_mapping():
    assert Globals.patient_mapping == {}


def test_globals_processed_data():
    assert Globals.processed_data == {}


def test_globals_raw_data():
    assert Globals.connected_devices == {}
