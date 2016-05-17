import mysql.connector as sqlc
import json
import sys, datetime
import utility as u
import sched, time

class Database:
    """
Handler for my arduino's JSON output.
    """
    def __init__(self, host, login, passwd, database, fields):
        """
Get necessary vars and set up tables.
        """
        self.host = host
        self.login = login
        self.passwd = passwd
        self.database = database
        self.labels = fields
        self._db = None
        st = self.show_tables()
        if not st is None and not len(st) > 1:
            self.create_table(fields)
            self.create_message_table()

    @property
    def conn(self):
        """
This is a cross between other connection properties I've seen
and my own experimentation for dealing with an annoyingly
intermittent connection.

I guess it'd be nice if it could wait a while and try again in
the event of a missing connection, but I suppose it just waits
60 seconds and then crashes.
        """
        try:
            if self._db is None:
                self._db = sqlc.connect(user=self.login,
                                        password=self.passwd,
                                        host=self.host,
                                        database=self.database)

        except sqlc.Error as e:
            print ("MySQL exception #{0} getting connection: {1}".format(e.errno, e.msg))
            if e.errno == 2003:
                exit(-1)
        except Exception as e:
            print ("Couldn't get connection property: {0}".format(e.message))
        finally:
            return self._db

    def cursor(self):
        """
Access the conn property and return a cursor.
        """
        return self.conn.cursor()

    def close(self):
        """
Commit, and close everything to ensure current records.
        """
        self.conn.commit()
        self.cursor().close()
        self.conn.close()
        self._db = None

    def get_db_version(self):
        """
Return db verison.
        """
        try:
            c = self.conn
            cur = c.cursor()
            cur.execute('SELECT VERSION();')
            data = cur.fetchone()
            return "MySQL/Maria DB version information:\n%s" % data
        except sqlc.Error as e:
            print ("MySQL exception #{0}: {1}".format(e.errno, e.msg))
            return None
        except Exception as e:
            msg = ""
            for arg in e.args:
                msg = msg + arg + "\n"
            print ("Couldn't get db version: {0}".format(msg))
            return None

    def show_tables(self):
        """
See what tables are in the db.
        """
        try:
            c = self.conn
            cur = c.cursor()
            sql = ("SHOW TABLES;")
            cur.execute(sql)
            return cur.fetchall()
        except sqlc.Error as e:
            print ("MySQL exception #{0}: {1}".format(e.errno, e.msg))
            return None
        except Exception as e:
            msg = ""
            for arg in e.args:
                msg = msg + arg + "\n"
            print ("Couldn't get list of tables: {0}".format(msg))
            return None

    def print_tables(self):
        """
List tables in the db.
        """
        print "------------------\nTables\n------------------"
        cnt = 0
        for x in self.show_tables():
            cnt += 1
            print ("{0}.) {1}".format(cnt, x[0]))

    def create_table(self, fields):
        """
Get fields we're gonna use from an array. All of them are
DECIMAL(10,2).
        """
        f = ' DECIMAL(10,2), '.join(fields)
        create_sql = ("CREATE TABLE IF NOT EXISTS snapshot_log "
                      "(id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                      "timestamp TIMESTAMP, " +
                      f + " DECIMAL(10,2) "
                      ")")
        cur = self.cursor()
        try:
            cur.execute(create_sql)
        except sqlc.Error as e:
            print ("MySQL exception #{0} creating table: {1}".format(e.errno, e.msg))
            return None
        except Exception as e:
            print ("Couldn't create table: {0}".format(e.message))
            return None
        finally:
            cur.close()

    def create_message_table(self):
        """
I thought it might be interesting to be able to look back at
when messages were sent, and using what platforms.
        """
        sql = ("CREATE TABLE IF NOT EXISTS message_log "
               "(id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
               "timestamp TIMESTAMP, "
               "message VARCHAR(1024), "
               "email INT(1), "
               "tweet INT(1), "
               "status INT(1))")
        cur = self.cursor()
        try:
            cur.execute(sql)
        except sqlc.Error as e:
            print ("Error #{0}: {1}\nCouldn't insert\nsql={2}"
                   .format(e.errno, e.msg, sql))
        except Exception as e:
            print ("Error: {0}\nCouldn't insert\nsql={1}"
                   .format(e.message, sql))
        finally:
            self.close()

    def insert_data(self, json_string):
        """
If the JSON is a dictionary constructed according to the `labels'
array in the config file, we can just insert it.
        """
        json_ob = json.loads(json_string)
        fields = ', '.join([f for f in json_ob])
        values = ', '.join([str(json_ob[u.unicode_to_string(f)])
                            for f in json_ob])
        sql = ("INSERT INTO snapshot_log (timestamp, " +
               fields  + ") VALUES (NOW(), " + values  +
               ")")
        cur = self.cursor()
        try:
            cur.execute(sql)
            #self.conn.commit()
        except sqlc.Error as e:
            print ("Error #{0}: {1}\nCouldn't insert\nsql={2}".
                   format(e.errno, e.msg, sql))
        except Exception as e:
            print ("Error: {0}\nCouldn't insert\nsql={1}".
                   format(e.message, sql))
        finally:
            self.close()

    def insert_dict(self, dict_data):
        """
If the Python dictionary is a dictionary constructed
according to the `labels' array in the config file, we can
just insert it.
        """
        fields = ', '.join([f for f in dict_data])
        values = ', '.join([str(dict_data[f]) for f in dict_data])
        sql = ("INSERT INTO snapshot_log (timestamp, " + fields +
               ") VALUES (NOW(), " + values + " )")

        cur = self.cursor()
        try:
            cur.execute(sql)
            #self.conn.commit()
        except sqlc.Error as e:
            print ("Error #{0}: {1}\nCouldn't insert\nsql={2}"
                   .format(e.errno, e.msg, sql))
        except Exception as e:
            print ("Error: {0}\nCouldn't insert\nsql={1}"
                   .format(e.message, sql))
        finally:
            self.close()

    def insert_alert(self, msg, email, tweet, stat):
        """
Insert a record into the message_log table.
        """
        sql = ("INSERT INTO message_log (timestamp, message, "
               "email, tweet, status) VALUES "
               "(NOW(), \"{0}\", {1}, {2}, {3});".
               format(msg, email, tweet, stat))

        cur = self.conn.cursor()
        try:
            cur.execute(sql)
            #self.conn.commit()
        except sqlc.Error as e:
            print ("Error #{0}: {1}\nCouldn't insert\nsql={2}".
                   format(e.errno, e.msg, sql))
        except Exception as e:
            print ("Error: {0}\nCouldn't insert\nsql={1}".
                   format(e.message, sql))
        finally:
            self.close()

    def get_last_record(self):
        """
Return the most recent record in the snapshot_log table, but
just the fields maching the `labels' array in the config file.
        """
        cur = self.cursor()
        sql = ("SELECT " + ', '.join(self.labels) +
               " FROM snapshot_log WHERE id = (SELECT MAX(id) FROM "
               "snapshot_log);")
        cur.execute(sql)
        rows = cur.fetchall()
        #cur.close()
        self.close()
        return rows

    def get_all_rows(self):
        """
Dump the snapshot_log table.
        """
        cur = self.cursor()
        sql = ("SELECT * FROM snapshot_log;")
        cur.execute(sql)
        r = cur.fetchall()
        #cur.close()
        self.close()
        return r

    # def get_reduced_log(self, name, compfunc, t):
    #     condition_start = []
    #     condition_end = []
    #     started = False
    #     idx = self.fields.index(name)
    #     for row in self.get_all_rows():
    #         if compfunc(t, row[idx]) and not started:
    #             condition_start.append(row[1])
    #         if not compfunc(t, row[idx]) and started:
    #             condition_end.append(row[2])
    #     return condition_start, condition_end

    # def reduce_log(self):
    #     with self.conn:
    #         cur = self.conn.cursor()
    #         for field in self.fields:
    #             starts, ends = self.get_reduced_log(field, lessthan,
    #                                                 650)
    #             sql = ("CREATE TABLE IF NOT EXISTS " + field +
    #                    "(id INTEGER PRIMARY KEY ASC, timestamp, "
    #                    "condition)")

    #             cur.execute(sql)
    #             idx = 0
    #             for t in starts:
    #                 sql = ("INSERT INTO " + field + " (timestamp, "
    #                        "condition) VALUES (?, ?)")
    #                 print(sql)
    #                 cur.execute(sql, (starts[idx], 1))
    #                 idx += 1
    #                 if idx < len(ends):
    #                     sql = ("INSERT INTO " + field + " (timestamp, "
    #                            "condition) VALUES (?, ?)")
    #                     print(sql)
    #                     cur.execute(sql, (ends[idx], 0))

    def get_last_record_dict(self):
        """
Get a Python dictionary of the last record. This can easily
serialize into JSON, or be urlencoded into a bunch of thingspeak
arguments.
        """
        sql = ("SELECT " + ', '.join(self.labels) +
               " FROM snapshot_log WHERE id = (SELECT MAX(id) FROM "
               "snapshot_log);")
        try:
            cur = self.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            res = dict_factory(cur, rows[0])
            #cur.close()
            self.close()
            return res
        except AttributeError as ae:
            print ("Can't get last record: {0}".format(ae.message))
        except Exception as e:
            print ("Can't get last record: {0}".format(e.message))
            return None

def dig_fields(json_data):
    """
This can be used to examine a JSON string and return a `labels'
array for the config file.
    """
    data = json.loads(json_data)
    fields = [f for f in data]
    return fields

def dict_factory(cursor, row):
    """
Return a Python dictionary from a cursor and a record.

I got this snippet from <http://www.cdotson.com/2014/06/
generating-json-documents-from-sqlite-databases-in-python/>
    """
    dic = {}
    for idx, col in enumerate(cursor.description):
        if isinstance(row[idx], unicode):
            dic[col[0]] = u.unicode_to_string(row[idx])
        else:
            dic[col[0]] = row[idx]
    return dic
