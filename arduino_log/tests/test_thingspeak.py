from unittest import TestCase
import random
from arduino_log import sqlite_interface as sqi
from arduino_log import thingspeak
from arduino_log import arduino_log

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'
fields = ['a', 'b', 'c']

class TestCreate(TestCase):
    def setUp(self):        
        self.s = sqi.sqlite_writer("/tmp/test.db", fields)
        self.s.insert_data(SAMPLE_JSON)
        self.q = sqi.sqlite_reader("/tmp/test.db", fields)
        
    def test_create_url(self):
        t = thingspeak.ThingspeakInterface('/home/juntunenkc/git/arduino_log/etc/arduino_log.json')
        u = t.create_url(self.q.get_last_record_dict())
        self.assertEquals(u, "field2=482&field3=-42&field1=5847&api_key=")

    #def test_send_data(self):
        #t = thingspeak.ThingspeakInterface('/home/juntunenkc/git/arduino_log/etc/arduino_log.json')
        #t.send_data()

    def tearDown(self):
        import os
        os.remove(self.s.db_filename)
