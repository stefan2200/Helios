import sqlite3
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import threading
import time
import os


class SQLiteWriter:
    db = None
    scan = 0
    todo = Queue(maxsize=0)
    db_file = None
    active = True

    _db_thread = None
    seen_entries = []

    def init(self, dbfile):
        if not os.path.exists(dbfile):
            print("Database file %s not found, creating new one" % dbfile)
            self.db = sqlite3.connect(self.db_file)
            cursor = self.db.cursor()
            cursor.execute('CREATE TABLE "scans" ('
                           '"id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'
                           '"start_url"  TEXT,'
                           '"domain"  TEXT,'
                           '"started"  DATETIME,'
                           '"ended"  DATETIME'
                           ');')

            cursor.execute('CREATE TABLE "results" ('
                           '"id"  INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,'
                           '"scan"  INTEGER,'
                           '"type"  TEXT,'
                           '"module"  TEXT,'
                           '"severity"  INTEGER,'
                           '"detected"  DATETIME,'
                           '"data"  TEXT);')


            self.db.commit()
            cursor.close()
            self.db.close()

    def open_db(self, database_file):
        self.db_file = database_file
        self.init(self.db_file)
        self._db_thread = threading.Thread(target=self.loop)

    def start(self, url, domain):
        self._db_thread.start()
        sql = '''INSERT INTO scans(start_url, domain ,started) VALUES(?,?,datetime('now'))'''
        self.todo.put((sql, (url, domain), "start"))

    def put(self, result_type, script, severity, text, allow_only_once=False):
        if allow_only_once:
            entry = [result_type, script]
            if entry in self.seen_entries:
                return
            self.seen_entries.append(entry)
        sql = '''INSERT INTO results(scan, type, module, severity, data, detected) 
        VALUES(?, ?, ?, ?, ?, datetime('now')
        )'''
        self.todo.put((sql, (self.scan, result_type, script, severity, text), "result"))

    def end(self):
        sql = '''UPDATE scans SET ended = datetime('now') WHERE id = %d''' % self.scan
        self.todo.put((sql, (), "end"))

    def loop(self):
        self.db = sqlite3.connect(self.db_file)
        while self.active:
            if self.todo.qsize() > 0:
                sql, args, output_type = self.todo.get()
                cur = self.db.cursor()
                cur.execute(sql, args)
                if output_type == "start":
                    self.scan = cur.lastrowid
                self.db.commit()
                if output_type == "end":
                    self.db.close()
                    self.active = False
            time.sleep(0.5)

