import sqlite3 as sql
import json
import sys, datetime
import utility as u

class sqlite_writer:
    def __init__(self, db_filename, fields):
        """
We of course need a target filename for an sqlite db. 
Secondly, we need a json template string. We can create a table to
pick up whatever the Arduino is laying down based on what it's laying
down.
"""
        self.db_filename = db_filename
        self.labels = fields

        try:
            self.conn = sql.connect(db_filename)
        except sql.Error, e:
            print "Error %s:" % e.args[0]
            sys.exit(1)

        try:
            if not len(self.show_tables()) > 1:
                self.create_table(fields)
                self.create_message_table()
        except sql.Error, e:
            print "Error %s:" % e.args[0]
            sys.exit(1)

    def get_db_version(self):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute('SELECT SQLITE_VERSION()')
            data = cur.fetchone()
            return "SQLite version: %s" % data

    def show_tables(self):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("SELECT NAME FROM sqlite_master WHERE "
                   "type = 'table';")
            cur.execute(sql)
            return cur.fetchall()

    def print_tables(self):
        print "------------------\nTables\n------------------"
        with self.conn:
            cur = self.conn.cursor()
            cnt = 0
            for x in self.show_tables():
                cnt += 1
                print ("{0}.) {1}".format(cnt, x[0]))

    def create_table(self, fields):
        f = ', '.join(fields)
        create_sql = ("CREATE TABLE IF NOT EXISTS snapshot_log " 
                      "(id INTEGER PRIMARY KEY ASC, timestamp, " +
                      f +
                      ")")

        with self.conn:
            cur = self.conn.cursor()
            cur.execute(create_sql)

    def create_message_table(self):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("CREATE TABLE IF NOT EXISTS message_log "
                   "(id INTEGER PRIMARY KEY ASC, timestamp, message, "
                   "email, tweet, status)")
            cur.execute(sql)

    def insert_data(self, json_string):
        json_ob = json.loads(json_string)
        fields = ', '.join([f for f in json_ob])
        values = ', '.join([str(json_ob [u.unicode_to_string(f)])
                            for f in json_ob])
        sql = ("INSERT INTO snapshot_log (timestamp, " +
               fields  + ") VALUES (datetime(\'now\'), " + values  +
               ")")
        
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(sql)

    def insert_dict(self, dict_data):
        fields = ', '.join([f for f in dict_data])
        values = ', '.join([str(dict_data[f]) for f in dict_data])
        sql = ("INSERT INTO snapshot_log (timestamp, " + fields +
               ") VALUES (datetime(\'now\'), " + values + " )")
        
        with self.conn:
            cur = self.conn.cursor()
            cur.execute(sql)
        
    def insert_alert(self, msg, email, tweet, stat):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("INSERT INTO message_log (timestamp, message, "
                   "email, tweet, status) VALUES "
                   "(datetime(\'now\'), \"{0}\", {1}, {2}, {3});".
                   format(msg, email, tweet, stat))

            try:
                cur.execute(sql)
            except:
                print ("Couldn't insert\nsql={0}".format(sql))

class sqlite_reader:
    def __init__(self, db_filename, fields):
        try:
            self.conn = sql.connect(db_filename)
        except sql.Error, e:
            print "Error %s:" % e.args[0]
            sys.exit(1)

        self.fields = fields
            
    def get_last_record(self):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("SELECT " + ', '.join(self.fields) +
                   " FROM snapshot_log ORDER BY id DESC LIMIT 1;")
            cur.execute(sql)
            rows = cur.fetchall()
            return rows

    def get_all_rows(self):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("SELECT * FROM snapshot_log;")
            cur.execute(sql)
            return cur.fetchall()

    def get_reduced_log(self, name, compfunc, t):
        condition_start = []
        condition_end = []
        started = False
        idx = self.fields.index(name)
        for row in self.get_all_rows():
            if compfunc(t, row[idx]) and not started:
                condition_start.append(row[1])
            if not compfunc(t, row[idx]) and started:
                condition_end.append(row[2])
        return condition_start, condition_end

    def reduce_log(self):
        with self.conn:
            cur = self.conn.cursor()
            for field in self.fields:
                starts, ends = self.get_reduced_log(field, lessthan,
                                                    650)
                sql = ("CREATE TABLE IF NOT EXISTS " + field +
                       "(id INTEGER PRIMARY KEY ASC, timestamp, condition)")
                
                cur.execute(sql)
                idx = 0
                for t in starts:
                    sql = ("INSERT INTO " + field + " (timestamp, "
                           "condition) VALUES (?, ?)")
                    print(sql)
                    cur.execute(sql, (starts[idx], 1))
                    idx += 1
                    if idx < len(ends):
                        sql = ("INSERT INTO " + field + " (timestamp, "
                               "condition) VALUES (?, ?)")
                        print(sql)
                        cur.execute(sql, (ends[idx], 0))

    def get_last_record_dict(self):
        with self.conn:
            cur = self.conn.cursor()
            sql = ("SELECT " + ', '.join(self.fields) +
                   " FROM snapshot_log ORDER BY id DESC LIMIT 1;")
            cur.execute(sql)
            rows = cur.fetchall()
            return dict_factory(cur, rows[0])

def greaterthan(a, b):
    return b > a

def lessthan(a, b):
    return a < b

def eq(a, b):
    return a == b

def dig_fields(json_data):
    data = json.loads(json_data)
    fields = [f for f in data]
    return fields

def dict_factory(cursor, row):
    """
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

if __name__ == "__main__":
    db = sqlite_writer('1.db', ['a', 'b', 'c'])
    print db.get_db_version()
    db.print_tables()
