#!/usr/bin/env python
import httplib, urllib, os, datetime, serial, smtplib, json
import sqlite_interface as sqli
import thingspeak as thsp
import utility as u

class arduino_log():
    """For processing Arduino output."""
    def __init__(self, config_file):
        """Variable-ize everything in the thingspeak config file."""
        with open(config_file) as data_file:
            self.config_data = json.load(data_file)
        self.local_db = self.config_data["localDB"]
        self.key = self.config_data["key"]
        self.api_key = self.config_data["api_key"]
        self.unit = self.config_data["unit"]
        self.smtp_server = self.config_data["smtp_server"]
        self.sender = self.config_data["sender"]
        self.recipients = self.config_data["recipients"]
        self.day_start = self.config_data["day_start"]
        self.day_end = self.config_data["day_end"]
        self.alerts = self.config_data["alerts"]
        self.thspfreq = self.config_data["thingspeak_freq"]
        self.ser = serial.Serial(self.config_data["serial_port"],
                                 self.config_data["baud"])
        self.sqlw = sqli.sqlite_writer(self.local_db,
                                       self.config_data["labels"])
        self.thingspeak = thsp.ThingspeakInterface(config_file)
        self.sent = {}
        for i in self.config_data["alerts"]:
            self.sent[i[0]] = [False, False, True]

        self.labels = self.config_data["labels"]

    def ok_to_send(self):
        return u.ok_to_send(self.day_start, self.day_end)

    def send_email(self, subj, msg):
        if len(self.sender) > 0 or len(self.recipients) < 1:
            try:
                sender = self.sender
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
                    smtpo.sendmail(sender, receivers, message)
                    return True
            except Exception, e:
                self.sqlw.insert_alert("Failure sending email: {0}"
                                       .format(e), 0, 0, 0)
                return False
        else:
            return False

    def log_data(self):
        line = self.ser.readline()
        data = self.decode_string(line, 0)
        if data is not None and len(data) > 0:
            self.check_alerts(data)
            self.sqlw.insert_dict(data)

    def log_data2(self):
        line = self.ser.readline()
        data = self.decode_string2(line, 0)
        self.check_alerts(data)
        if data is not None and len(data) > 0:
            self.sqlw.insert_dict(data)

    def check_alerts(self, datadict):
        for alert in self.alerts:
            k = alert[0]
            v = alert[1]
            currentval = datadict[k]
            try:
                if abs(currentval) > abs(v):
                    if not self.sent[k][0]:
                        m = alert[2]
                        self.send_alert(m)
                        self.sent[k] = [True, False, False]
                if len(alert) > 4:
                    v = alert[3]
                    m = alert[4]
                    if abs(currentval) < abs(v):
                        if not self.sent[k][1]:
                            self.send_alert(m)
                            self.sent[k] = [False, True, False]
                if len(alert) > 5:
                    if (not self.sent[k][2] and not
                        abs(currentval) > abs(alert[1]) and not
                        abs(currentval) < abs(alert[3])):
                        m = alert[5]
                        self.send_alert(m)
                        self.sent[k] = [False, False, True]
            except Exception as e:
                print "Exception: {0}\n".format(e)

    def send_alert(self, msg):
        message = msg + " in " + str(self.unit).lower()
        # Tweet
        tsent = 0
        esent = 0
        if self.thingspeak.tweet(message):
            tsent = 1
            # Email between certain hours
        if self.ok_to_send():
            if self.send_email(self.unit, message):
                esent = 1
        self.sqlw.insert_alert(message, esent, tsent, 0)

    def check_return(self, datadict):
        for a in self.alerts:
            try:
                b = u.unicode_to_string(a)
                if abs(datadict [b]) < abs(self.config_data[b]):
                    if self.ok_to_send() and self.sent[b]:
                        message = b + " returned to normal in " + self.unit
                        esent = 0
                        if self.send_email(self.unit, message):
                            esent = 1
                        tsent = 0
                        if self.thingspeak.tweet(message):
                            tsent = 1
                        self.sqlw.insert_alert(message, esent, tsent, 0)
                        self.sent[b] = False
            except Exception as e:
                print "Exception: {0}\n".format(e)

    def decode_string(self, line, skip):
        try:
            json_ob = json.loads(line)
            if json_ob.has_key("Poll"):
                return json_ob["Poll"]
        except ValueError as ve:
            return None

    def decode_string2(self, line, skip):
        data = {}
        line_array = line.split(":")
        if not len(line_array) == len(self.labels) + abs(skip):
            return data
        count = abs(skip) * -1
        for field in line_array:
            if count > -1:
                try:
                    data[u.unicode_to_string(self.labels[count])] = float(field)
                except:
                    return data
            count += 1
        return data

    def loop(self):
        while True:
            try:
                self.log_data()
            except Exception as e:
                print("Exception: {0}\n".format(e.message))
                exit(1)

def start():
    import ip as ip
    ip.broadcast_ip()
    moni = arduino_log('/etc/arduino_log.json')
    moni.loop()


if __name__ == "__main__":
    start()
