from unittest import TestCase
import random
from arduino_log import sqlite_interface as sqi

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'
fields = ['a', 'b', 'c']

class TestCreate(TestCase):
    def setUp(self):        
        self.s = sqi.sqlite_writer("/tmp/test.db", fields)
        self.s.insert_data(SAMPLE_JSON)
        random.seed()
        x = random.randrange(1, 500000) / 1000.0
        self.s.insert_data('{"a": 5847, "b": ' + str(x)  + ', "c": 482}')
        self.q = sqi.sqlite_reader("/tmp/test.db", fields)
        
    def test_sqlite_create(self):
        self.s.print_tables()

    def test_insert_data(self):
        x = 0
        for i in range(500):
            v = random.randrange(1, 500000) / 1000.0
            w = random.randrange(1, 500000) / 1000.0
            x = random.randrange(1, 500000) / 1000.0
            self.s.insert_data('{"a": ' + str(v) + ', "b": ' + str(x)  + ', "c": ' + str(w) + '}')
            
        x = random.randrange(1, 500000) / 1000.0
        self.s.insert_data('{"a": 657, "b": ' + str(x)  + ', "c": 754}')

        y = self.q.get_last_record()[0]
        self.assertEqual(y[1], x)

    def test_read_data(self):
        lr = self.q.get_last_record()[0]
        self.assertEqual(lr[0], 5847)
        self.assertEqual(lr[2], 482)

    def tearDown(self):
        import os
        os.remove(self.s.db_filename)
