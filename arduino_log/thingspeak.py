"""I'll try and create a bunch of Thingspeak-specific functions."""
import json, urllib, httplib, sched, time
import sqlite_interface as sqli

class ThingspeakInterface():
    """A class for handling Thingspeak operations."""
    def __init__(self, config_data_file, json_template):
        with open(config_data_file) as config_file_handle:
            config_data = json.load(config_file_handle)
            self.key = config_data["key"]
            self.api_key = config_data["api_key"]
            self.target_db = config_data["localDB"]
        self.sqlr = sqli.sqlite_reader(self.target_db, json_template)
        self.sqlw = sqli.sqlite_writer(self.target_db, json_template)
        self.s = sched.scheduler(time.time, time.sleep)

    def tweet(self, message):
        """Use the Thingspeak API to tweet."""
        params = urllib.urlencode(
            {'api_key': self.api_key,
             'status': message})

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
            return True, message
        except httplib.HTTPException as http_exception:
            return False, http_exception.message
        
    def create_url2(self, json_string):
        data = json.loads(json_string)
        params = urllib.urlencode(data)
        return params

    def create_url(self, data_dict):
        data = {}
        count = 1
        for field in data_dict:
            data["field" + str(count)] = data_dict[field]
            count += 1

        data["api_key"] = self.api_key
        return urllib.urlencode(data)
        
    def send_data(self):
        """Send data to thingspeak."""
        #data = json.loads(json_string)
        params = self.create_url(self.sqlr.get_last_record_dict())
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = httplib.HTTPConnection("api.thingspeak.com:80")
        try:
            conn.request("POST", "/update", params, headers)
            response = conn.getresponse()
            #print response.status, response.reason
            data = response.read()
            conn.close()
            #return True, "OK"
            self.s.enter(30, 1, self.send_data, ())
        except httplib.HTTPException as http_exception:
            self.sqlw.insert_alert("Connection failed: {0}".format(http_exception.message), 0,0,0)
            #return False, "Connection failed: {0}".format(http_exception.message)
            self.s.enter(240, 1, self.send_data, ())

    def start_loop(self, json_string, timespec):
        self.s.enter(30, 1, self.send_data, ())
        self.s.run()
