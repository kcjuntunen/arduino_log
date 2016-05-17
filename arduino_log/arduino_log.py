#!/usr/bin/env python
import datetime, serial, smtplib, json
import mysql_interface as sqli
from threading import Timer, Thread
import thingspeak as thsp
import ip
import utility as u
from SocketServer import BaseRequestHandler, TCPServer

ARDUINO_POLL = '\x12' # Device Control 2
CURRENT_RFID = 0x00000000

class EchoHandler(BaseRequestHandler):
    """

    """
    def handle(self):
        try:
            # print "Client connected:", self.client_address
            # received = self.request.recv(2**16)
            global CURRENT_RFID # so multiple threads can touch it
                                # is that a bad idea? It seems to work.
            self.request.sendall(str(CURRENT_RFID) + "\n")
        except Exception as e:
            print "Couldn't send '{0}': {1}".format(str(CURRENT_RFID), e.message)
        finally:
            self.request.close()

class arduino_log():
    """
For processing Arduino output.
    """
    def __init__(self, config_file):
        """
Variable-ize everything in the thingspeak config file. TODO: Put this
stuff all in an update function. That way, perhaps, the variables
could be updated while arduino-log is running.
        """
        with open(config_file) as data_file:
            self.config_data = json.load(data_file)
        self.local_db = self.config_data["localDB"]
        self.key = self.config_data["key"]
        self.api_key = self.config_data["api_key"]
        self.unit = self.config_data["unit"]
        self.smtp_server = self.config_data["smtp_server"]
        self.sender = self.config_data["sender"]
        self.passwd = self.config_data["passwd"]
        self.recipients = self.config_data["recipients"]
        self.day_start = self.config_data["day_start"]
        self.day_end = self.config_data["day_end"]
        self.alerts = self.config_data["alerts"]
        self.logfreq = self.config_data["log_freq"]
        self.thspfreq = self.config_data["thingspeak_freq"]
        self.ser = serial.Serial(self.config_data["serial_port"],
                                 self.config_data["baud"])
        self.sqlw = sqli.Database(self.config_data["host"],
                                  self.config_data["login"],
                                  self.config_data["passwd"],
                                  self.config_data["database"],
                                  self.config_data["labels"])
        self.thingspeak = thsp.ThingspeakInterface(config_file)
        self.sentinlastfive = False
        self.sent = {}
        for i in self.config_data["alerts"]:
            self.sent[i[0]] = [False, False, True]

        self.labels = self.config_data["labels"]

    def toggle_sentinlastfive(self):
        self.sentinlastfive = not self.sentinlastfive

    def poll(self):
        if self.logfreq > 1:
            self.ser.write(ARDUINO_POLL)
            Timer(self.logfreq, self.poll, ()).start()
        else:
            print("Not polling")

    def ok_to_send(self):
        return u.ok_to_send(self.day_start, self.day_end)

    def send_email(self, subj, msg):
        """
Sends an email. subj, and msg are self-explanatory. TODO: Make it
clever enough to support passwords.
        """
        if (len(self.sender) > 0 or len(self.recipients) < 1):
            try:
                sender = self.sender
                passwd = self.passwd
                receivers = self.recipients
                message = "From: " + self.unit  + " <no_real_email@nobody.com>"
                message += "\nTo: "

                rec_cnt = len(receivers)
                cnt = 1
                for s in receivers:
                    message += "<" + s
                    message += ">"
                    if cnt < rec_cnt:
                        message += ", "

                    message += "\nSubject: "

                    message += subj + "\n\n"
                    message += msg + "\n"
                    smtpo = smtplib.SMTP(self.smtp_server)
                    smtpo.starttls()
                    smtpo.login(sender.split('@', 1)[0], passwd)
                    smtpo.sendmail(sender, receivers, message)
                    smtpo.quit()
                    return True
            except Exception as e:
                errmsg = "Failure sending email: {0}".format(e.message)
                print errmsg
                self.sqlw.insert_alert(errmsg, 0, 0, 0)
                return False
        else:
            return False

    def process_line(self, line):
        """
When a line is received, process it conditionally.

        { "Poll": { dict here } } -> record to snapshot log
        { "RFID": { dict here } } -> Drop RFID info somewhere useful
        { "Event": { dict here } } ->  Log to event db
        """
        try:
            json_ob = json.loads(line)
            if json_ob.has_key("Poll"):
                self.log_snapshot(json_ob["Poll"])
            if json_ob.has_key("RFID"):
                self.process_rfid(json_ob["RFID"])
            if json_ob.has_key("Event"):
                self.process_event(json_ob["Event"])
        except ValueError as ve:
            # Not JSON
            pass

    def listen(self):
        """
This is sort of the entry point. Put it inside a loop, and it'll act
on certain JSON strings. As of now, I'm just dumbly using readline, so
the JSON string can't have newlines inside it.
        """
        line = self.ser.readline()
        self.process_line(line)

    def log_snapshot(self, data):
        """
Check if certain thresholds have been overrun.  Send a proper
dictionary to the sql interface class.  TODO: DB should be
optional. Merely sending alerts would be useful.
        """
        if data is not None and len(data) > 0:
            self.check_alerts(data)
            self.sqlw.insert_dict(data)

    def process_rfid(self, data):
        """
Drop this data somewhere it'll be visible to apache/httpd and php.
Updates the current_rfid bar variable, which is served by a little
SocketServer.
        """
        try:
            global CURRENT_RFID # so multiple threads can touch it
                                # is that a bad idea? It seems to work.
            CURRENT_RFID = data["UID"]
        except Exception as e:
            print ("Exception: {0}\n"
                   "Couldn't get UID; data={1}".format(e.message, data))

    def process_event(self, data):
        """
Cleverly store event data in a db. I can't imagine a way to handle
this without a definition in the config file.
        """
        pass

    def check_alerts(self, datadict):
        """
Here, a dictionary is examined accoring to thresholds set in the
config file.
        """
        for alert in self.alerts:
            k = alert[0]
            currentval = datadict[k]
            try:
                if len(alert) > 2:
                    v = alert[1]
                    if (currentval > v and
                        not self.sent[k][0]):
                        m = alert[2]
                        self.send_alert(m)
                        self.sent[k] = [True, False, False]
                if len(alert) > 4:
                    v = alert[3]
                    m = alert[4]
                    if (currentval < v and
                        not self.sent[k][1]):
                        self.send_alert(m)
                        self.sent[k] = [False, True, False]
                if len(alert) > 5:
                    v1 = alert[1]
                    v2 = alert[3]
                    if (not self.sent[k][2] and not
                        currentval > v1 and not
                        currentval < v2):
                        m = alert[5]
                        self.send_alert(m)
                        self.sent[k] = [False, False, True]
            except Exception as e:
                print "Check alerts exception: {0}\n".format(e.message)
                count = 1
                for arg in e.args:
                    print "{0} - {1}".format(count, arg)
                    count = count + 1

    def send_alert(self, msg):
        """
Currently, there are two places to send alerts: twitter, and email.
Lots of email is annoying so it can only send every 5 minutes.
        """
        today = datetime.datetime.now()
        message = (msg + " in " + str(self.unit).lower() +
                   " @ " + today.strftime('%b %d %Y %H:%M'))
        # Tweet
        # The reason I had to pull in the thingspeak handling class,
        # is that I'm using the thingspeak API to tweet.
        tsent = 0
        esent = 0
        if self.thingspeak.tweet(message):
            tsent = 1
        # Email between certain hours
        if self.ok_to_send() and not self.sentinlastfive:
            if self.send_email(self.unit, message):
                esent = 1
                self.sentinlastfive = True
                Timer(300, self.toggle_sentinlastfive).start()
        self.sqlw.insert_alert(message, esent, tsent, 0)

    def start_rfid_server(self, port):
        TCPServer(('', port), EchoHandler).serve_forever()


    def loop(self):
        if (("rfid_port" in self.config_data) and
            (self.config_data ["rfid_port"] > 1024)):
            Thread(target=self.start_rfid_server,
                   args=(int(self.config_data ["rfid_port"]),)).start()
            # self.start_rfid_server(int(self.config_data ["rfid_port"]))

        while True:
            try:
                self.listen()
            except Exception as e:
                print("Couldn't read serial input: {0}\n".format(e.message))

def start():
    ip.broadcast_ip()
    moni = arduino_log('/etc/arduino_log.json')
    moni.poll()
    moni.loop()


if __name__ == "__main__":
    start()
