from unittest import TestCase
import mock
import random
from arduino_log import arduino_log

SAMPLE_JSON = '{"a": 5847, "b": -42, "c": 482}'

class TestCreate(TestCase):
    @mock.patch('serial.Serial')
    def setUp(self, mock_ser):
        self.a = arduino_log.arduino_log('./etc/arduino_log.json')

    def test_decode_string(self):
        b = self.a.decode_string("{\"Poll\":" + SAMPLE_JSON  + " }", 0)

    def test_decode_string2(self):
        x = random.randrange(1, 5000000 )/ 1000.0
        b = self.a.decode_string2("58386:5847:" + str(x) + ":482", 0)
        b = self.a.decode_string2("58386:5847:" + str(x) + ":482", 1)

    @mock.patch('smtplib.SMTP')
    def test_send_email(self, mock_smtp):
        self.a.sender = "me@nope.net"
        self.a.recipients = ['fake_email@gmail.com', 'another_fake@gmail.com']
        self.a.send_email("stuff", "things")

    def test_log_data2(self):
        self.a.log_data2()

    def test_check_alerts_returns(self):
        self.a.check_alerts({'a': 40, 'c': 55})
        self.a.check_alerts({'a': 5100, 'c': -500})
        self.a.check_return({'a': 5100, 'c': -500})
        self.a.check_return({'a': 40, 'c': 55})
