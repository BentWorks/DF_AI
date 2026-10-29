"""Durable record of every action the controller takes, so retries reconcile instead of repeating."""
import json
import sqlite3
import time
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE,                 -- idempotency key (caller-supplied or derived)
  kind TEXT NOT NULL,
  params TEXT NOT NULL,
  execution_status TEXT NOT NULL,  -- requested | applied | blocked | failed | unknown
  result TEXT,
  game_tick INTEGER,
  created REAL NOT NULL,
  updated REAL NOT NULL
);
"""


class Ledger:
    def __init__(self, path=None):
        self.db = sqlite3.connect(str(path or config.RUN_DIR / "ledger.sqlite"), check_same_thread=False)
        self.db.execute(SCHEMA)
        self.db.commit()

    def get(self, key):
        row = self.db.execute("SELECT id,key,kind,params,execution_status,result,game_tick FROM actions WHERE key=?", (key,)).fetchone()
        return self._row(row) if row else None

    def start(self, key, kind, params, tick=None):
        now = time.time()
        self.db.execute("INSERT INTO actions(key,kind,params,execution_status,game_tick,created,updated) VALUES(?,?,?,?,?,?,?)",
                        (key, kind, json.dumps(params), "requested", tick, now, now))
        self.db.commit()

    def finish(self, key, status, result):
        self.db.execute("UPDATE actions SET execution_status=?, result=?, updated=? WHERE key=?",
                        (status, json.dumps(result), time.time(), key))
        self.db.commit()

    def recent(self, limit=20):
        rows = self.db.execute("SELECT id,key,kind,params,execution_status,result,game_tick FROM actions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r):
        return {"id": r[0], "key": r[1], "kind": r[2], "params": json.loads(r[3]), "execution_status": r[4],
                "result": json.loads(r[5]) if r[5] else None, "game_tick": r[6]}
