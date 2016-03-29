from unittest import TestCase
import random
from arduino_log import sqlite_interface as sqi
from arduino_log import thingspeak
from arduino_log import arduino_log

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'

class TestCreate(TestCase):
    def setUp(self):        
        self.s = sqi.sqlite_writer("/tmp/test.db", SAMPLE_JSON)
        self.q = sqi.sqlite_reader("/tmp/test.db", SAMPLE_JSON)
        
    def test_create_url(self):
        t = thingspeak.ThingspeakInterface('/home/juntunenkc/git/arduino_log/etc/arduino_log.json', SAMPLE_JSON)
        u = t.create_url(self.q.get_last_record_dict())
        print(u)
        self.assertGreater(len(u), 1)

    def test_send_data(self):
        t = thingspeak.ThingspeakInterface('/home/juntunenkc/git/arduino_log/etc/arduino_log.json', SAMPLE_JSON)
        t.send_data()
