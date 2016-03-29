from unittest import TestCase
import random
from arduino_log import sqlite_interface as sqi
from arduino_log import thingspeak
from arduino_log import arduino_log

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'

class TestCreate(TestCase):
    def test_decode_string(self):
        a = arduino_log.arduino_log('/home/juntunenkc/git/arduino_log/etc/arduino_log.json', SAMPLE_JSON)
        x = random.randrange(1, 5000000 )/ 1000.0
        b = a.decode_string("58386:5847:" + str(x) + ":482")
        print(b)
