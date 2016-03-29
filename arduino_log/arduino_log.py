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
            self.threshold = self.config_data["light_threshold"]
            self.day_start = self.config_data["day_start"]
            self.day_end = self.config_data["day_end"]
            self.alerts = self.config_data["alerts"]
            self.ser = serial.Serial(self.config_data["serial_port"],
                                     self.config_data["baud"])
        self.sqlw = sqli.sqlite_writer(self.local_db,
                                       self.config_data["labels"])
        self.thingspeak = thsp.ThingspeakInterface(config_file)
        self.sent_on = True
        self.sent_off = False
        self.labels = self.config_data["labels"]

    def ok_to_send(self):
        return u.ok_to_send(self.day_start, self.day_end)

    def send_email(self, subj, msg):
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

    def send_data2(self):
        try:
            l = self.ser.readline()
            line = l.split(":")
        except:
            msg = "Couldn't split string: "
            if l:
                msg += l
            self.sqlw.insert_alert(msg, 0, 0, 0);

        try:
            self.sqlw.insert_ser_line(l)
        except:
            print "Couldn't insert data."

        paramsd = {'field1': line[1],
                   'field2': line[2],
                   'field3': line[3],
                   'field4': line[4],
                   'field5': line[5],
                   'field6': line[6],
                   'field7': os.getloadavg()[0],
                   'field8': line[7],
                   'key': self.key}

        if float(line[4]) < self.threshold:
            if not self.sent_off:
                today = datetime.datetime.now()
                paramsd['status'] = "Lights are out."
                msg = "The lights are out in {0}. ({1} UTC)".format(
                    self.unit, today.strftime('%b %d %Y %H:%M'))
                t = 0
                if self.thingspeak.tweet(msg):
                    t = 1
                e = 0
                if self.ok_to_send() and self.send_email(paramsd['status'], msg):
                    e = 1

                self.sqlw.insert_alert("Lights are out.", e, t, 1)
                self.sent_off = True
                self.sent_on = False

        if float(line[4]) > self.threshold:
            if not self.sent_on:
                today = datetime.datetime.now()
                paramsd['status'] = "Lights are back on."
                msg = "The lights are back on in {0}. ({1} UTC)".format(
                    self.unit, today.strftime('%b %d %Y %H:%M'))
                t = 0
                if self.thingspeak.tweet(msg):
                    t = 1
                e = 0
                if self.ok_to_send() and self.send_email(paramsd['status'], msg):
                    e = 1

                self.sqlw.insert_alert("Lights are back on.", 0, t, 1)
                self.sent_on = True
                self.sent_off = False

        params = urllib.urlencode(paramsd)

        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}

        conn = httplib.HTTPConnection("api.thingspeak.com:80")

        try:
            conn.request("POST", "/update", params, headers)
            response = conn.getresponse()
            #print response.status, response.reason
            data = response.read()
            conn.close()
        except:
            self.sqlw.insert_alert("Connection failed", 0, 0, 0)

    def process_data(self, json_ob):
        # Instead of millis:presence:lrs:srs:ll:hum:temp:lt:pir,
        # how about
        # {
        #     "millis()": 4373838,        
        #     "distance": 600,
        #     "Switch1": 0,
        #     "Switch2": 0,
        #     "LightLevel": 300,
        #     "Humidity": 28,
        #     "Temperature": 72,
        #     "Pressure": 1011,            
        # }
        data = json.load(json_ob)

    def log_data(self, ser):
        while True:
            line = ser.readline()
            data = self.decode_string(line)
            self.check_alerts(data)
            self.sqlw.insert_dict(data)

    def check_alerts(self, datadict):
        for a in self.alerts:
            if datadict[a] > abs(self.config_data[a]):
                if self.ok_to_send():
                    self.send_email(self.unit, a + " exceeded.")
                    self.thingspeak.tweet(a + " exceeded in " + self.unit)

    def decode_string(self, line):
        data = {}
        line_array = line.split(":")
        if not len(line_array) == len(self.labels) + 1:
            return data
        count = -1
        for field in line_array:
            if count > -1:
                data[u.unicode_to_string(self.labels[count])] = float(field)
            count += 1
        return data

    def loop(self):
        while True:
            try:
                self.send_data2()
            except Exception as e:
                self.sqlw.insert_alert("Exception: {0}".format(e), 0, 0, 0)

def start():    
    import ip as ip
    ip.broadcast_ip()
    moni = arduino_log('/etc/ardino_log.json')
    moni.loop()


if __name__ == "__main__":
    start()

