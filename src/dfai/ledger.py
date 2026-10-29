"""Durable record of every mutating action, so retries reconcile instead of repeating.

Records are scoped to a fortress identity (world + site). A request key is unique per fortress; reusing a key
with different parameters is a conflict. Unresolved records (requested/unknown) are never reported as done:
callers reconcile them against game evidence. If the game clock moves backwards (a reload of an earlier save),
open records from later game time are marked stale.
"""
import json
import sqlite3
import time
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fort TEXT NOT NULL,              -- fortress identity: world name + site id
  key TEXT NOT NULL,               -- request identity (caller-supplied or generated)
  kind TEXT NOT NULL,
  params TEXT NOT NULL,
  execution_status TEXT NOT NULL,  -- requested | applied | blocked | failed | unknown | stale
  evidence TEXT,                   -- pre-action evidence used for reconciliation
  result TEXT,
  game_tick INTEGER,
  created REAL NOT NULL,
  updated REAL NOT NULL,
  UNIQUE(fort, key)
);
CREATE TABLE IF NOT EXISTS forts (fort TEXT PRIMARY KEY, last_tick INTEGER);
"""


class Ledger:
    def __init__(self, path=None):
        self.db = sqlite3.connect(str(path or config.RUN_DIR / "ledger_v2.sqlite"), check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def observe_tick(self, fort, tick):
        """Detect reloads: if game time went backwards, open records after `tick` become stale."""
        row = self.db.execute("SELECT last_tick FROM forts WHERE fort=?", (fort,)).fetchone()
        stale = 0
        if row and tick < row[0]:
            stale = self.db.execute("UPDATE actions SET execution_status='stale', updated=? WHERE fort=? AND game_tick>? "
                                    "AND execution_status IN ('requested','unknown','applied')", (time.time(), fort, tick)).rowcount
        self.db.execute("INSERT INTO forts(fort,last_tick) VALUES(?,?) ON CONFLICT(fort) DO UPDATE SET last_tick=excluded.last_tick", (fort, tick))
        self.db.commit()
        return stale

    def get(self, fort, key):
        row = self.db.execute("SELECT * FROM actions WHERE fort=? AND key=?", (fort, key)).fetchone()
        return self._row(row) if row else None

    def start(self, fort, key, kind, params, tick, evidence=None):
        now = time.time()
        self.db.execute("INSERT INTO actions(fort,key,kind,params,execution_status,evidence,game_tick,created,updated) "
                        "VALUES(?,?,?,?,?,?,?,?,?)", (fort, key, kind, json.dumps(params, sort_keys=True), "requested",
                                                       json.dumps(evidence), tick, now, now))
        self.db.commit()

    def finish(self, fort, key, status, result):
        self.db.execute("UPDATE actions SET execution_status=?, result=?, updated=? WHERE fort=? AND key=?",
                        (status, json.dumps(result), time.time(), fort, key))
        self.db.commit()

    def recent(self, fort, limit=20):
        rows = self.db.execute("SELECT * FROM actions WHERE fort=? ORDER BY id DESC LIMIT ?", (fort, limit)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r):
        return {"id": r[0], "fort": r[1], "key": r[2], "kind": r[3], "params": json.loads(r[4]), "execution_status": r[5],
                "evidence": json.loads(r[6]) if r[6] else None, "result": json.loads(r[7]) if r[7] else None, "game_tick": r[8]}
