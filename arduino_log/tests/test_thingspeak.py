from unittest import TestCase
import random
import mock
from arduino_log import sqlite_interface as sqi
from arduino_log import thingspeak
from arduino_log import arduino_log

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'
fields = ['a', 'b', 'c']

class TestCreate(TestCase):
    def setUp(self):
        self.t = thingspeak.ThingspeakInterface('./etc/arduino_log.json')
        #self.s.insert_data(SAMPLE_JSON)
        
    def test_create_url(self):
        u = self.t.create_url(self.t.sqlr.get_last_record_dict())
        #self.assertEquals(u, "field2=482&field3=-42&field1=5847&key=")

    @mock.patch('httplib.HTTPConnection')
    def test_tweet(self, mock_httplib):
        self.t.api_key = "blah"
        self.t.tweet("a message")        

    @mock.patch('httplib.HTTPConnection')
    def test_send_data(self, mock_httplib):
        self.t.key = "blah"
        self.t.send_data()

    # I don't know how I'm supposed to test loops and timers, &c. Takes too long.
    # @mock.patch('sched.scheduler')
    # def test_start_loop(self, mock_scheduler):
    #     self.t.timespec = 14
    #     self.t.start_loop()
        
    def tearDown(self):
        None
        #import os
        #os.remove(self.s.db_filename)
