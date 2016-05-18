"""I'll try and create a bunch of Thingspeak-specific functions."""
import json, urllib, httplib, sched, time
import mysql_interface as sqli
import HTMLParser

class TagStripper(HTMLParser.HTMLParser):
    collected_data = ""
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)

    def handle_data(self, data):
        self.collected_data = self.collected_data + data

    def get_collected_data(self):
        return self.collected_data

class ThingspeakInterface():
    """A class for handling Thingspeak operations."""
    def __init__(self, config_data_file):
        with open(config_data_file) as config_file_handle:
            config_data = json.load(config_file_handle)
            self.key = config_data["key"]
            self.api_key = config_data["api_key"]
            self.target_db = config_data["localDB"]
            self.labels = config_data["labels"]
            self.timespec = config_data["thingspeak_freq"]
            self.sqlr = sqli.Database(config_data["host"],
                                      config_data["login"],
                                      config_data["passwd"],
                                      config_data["database"],
                                      config_data["labels"])
        self.s = sched.scheduler(time.time, time.sleep)

    def tweet(self, message):
        """Use the Thingspeak API to tweet."""
        if self.api_key == "":
            return False
        ts = TagStripper()
        ts.feed(message)
        params = urllib.urlencode(
            {'api_key': self.api_key,
             'status': ts.get_collected_data()})

        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}

        conn = httplib.HTTPConnection("api.thingspeak.com:80")

        try:
            conn.request("POST",
                         "/apps/thingtweet/1/statuses/update",
                         params,
                         headers)

            response = conn.getresponse()
            data = response.read()
            conn.close()
            return True, ts.get_collected_data()
        except httplib.HTTPException as http_exception:
            return False, http_exception.message

    def create_url(self, data_dict):
        data = {}
        count = 1
        for field in self.labels:
            data["field" + str(count)] = data_dict[field]
            count += 1

        data["key"] = self.key
        return urllib.urlencode(data)

    def send_data(self):
        """Send data to thingspeak."""
        if self.key == "":
            return False
        try:
            params = self.create_url(self.sqlr.get_last_record_dict())
            headers = {"Content-type": "application/x-www-form-urlencoded",
                       "Accept": "text/plain"}
            conn = httplib.HTTPConnection("api.thingspeak.com:80")
            conn.request("POST", "/update", params, headers)
            response = conn.getresponse()
            #print ("{0}, {1}".format(response.status, response.reason))
            data = response.read()
            conn.close()
            self.s.enter(self.timespec, 1, self.send_data, ())
        except httplib.HTTPException as http_exception:
            self.sqlr.insert_alert("Connection failed: {0}".
                                   format(http_exception.message), 0,0,0)
            print("Connection failed: {0}".format(http_exception.message))
            # try again in 5
            self.s.enter(300, 1, self.send_data, ())
        except Exception as e:
            print("I'm the guy killing your script: {0}".format(e.message))
            # try again in 5
            self.s.enter(300, 1, self.send_data, ())

    def start_loop(self):
        self.s.enter(5, 1, self.send_data, ())
        self.s.run()

def start(config_file):
    thsp = ThingspeakInterface(config_file)
    thsp.start_loop()
