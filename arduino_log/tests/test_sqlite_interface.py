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
        
    def test_sqlite_create(self):
        self.s.print_tables()

    def test_insert_data(self):
        random.seed()
        x = random.randrange(1, 500000) / 1000.0
        self.s.insert_data('{"a": 5847, "b": ' + str(x)  + ', "c": 482}')
        self.assertEqual(self.q.get_last_record()[0][2], x)

    def test_read_data(self):
        lr = self.q.get_last_record()[0]
        self.assertEqual(lr[0], 5847)
        self.assertEqual(lr[1], 482)
