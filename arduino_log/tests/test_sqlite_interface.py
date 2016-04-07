from unittest import TestCase
import random
import time
import logging
from arduino_log import sqlite_interface as sqi

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'
fields = ['a', 'b', 'c']

class TestCreate(TestCase):
    def setUp(self):
        logging.basicConfig(filename='/tmp/test.log',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            level=logging.DEBUG)
        self.s = sqi.sqlite_writer("/tmp/test.db", fields)
        self.s.insert_data(SAMPLE_JSON)
        random.seed()
        x = gimmie_a_number()
        self.s.insert_data('{"a": 5847, "b": ' + str(x)  + ', "c": 482}')

        for i in range(10):
            v = gimmie_a_number()
            w = gimmie_a_number()
            x = gimmie_a_number()
            self.s.insert_data('{"a": ' + str(v) + ', "b": ' + str(x)  + ', "c": ' + str(w) + '}')
            #time.sleep(1)

        self.q = sqi.sqlite_reader("/tmp/test.db", fields)

    def test_get_db_version(self):
        self.s.get_db_version()

    def test_insert_data(self):
        x = random.randrange(1, 500000) / 1000.0
        self.s.insert_data('{"a": 657, "b": ' + str(x)  + ', "c": 754}')

        y = self.q.get_last_record()[0]
        self.assertEqual(y[1], x)

    def test_read_data(self):
        self.s.insert_data('{"a": 5847, "b": -42, "c": 482}')
        lr = self.q.get_last_record()[0]
        self.assertEqual(lr[0], 5847)
        self.assertEqual(lr[2], 482)

    def test_get_all_rows(self):
        all_rows = self.q.get_all_rows()
        self.assertGreater(len(all_rows), 500)

    # Not using these (yet?)
    # def test_get_reduced_log(self):
    #     starts, ends = self.q.get_reduced_log('a', sqi.lessthan, 998.11)
    #     for x in starts:
    #         logging.debug(x + "1")
    #     for x in ends:
    #         self.logger.debug(x + "0")

    # def test_reduce_log(self):
    #     self.q.reduce_log()

    def tearDown(self):
        None
        #import os
        #os.remove(self.s.db_filename)

def gimmie_a_number():
    return random.randrange(1, 500000) / 1000.0
