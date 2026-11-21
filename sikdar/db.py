"""SQLite persistence layer."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS clients (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    phone            TEXT NOT NULL DEFAULT '',
    email            TEXT NOT NULL DEFAULT '',
    aadhar           TEXT NOT NULL DEFAULT '',
    pan              TEXT NOT NULL DEFAULT '',
    dob              TEXT NOT NULL DEFAULT '',
    address          TEXT NOT NULL DEFAULT '',
    photo            TEXT NOT NULL DEFAULT '',
    portal_password  TEXT NOT NULL DEFAULT '',
    gst_id           TEXT NOT NULL DEFAULT '',
    gst_password     TEXT NOT NULL DEFAULT '',
    folder_name      TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'Active',
    notes            TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    due_date   TEXT NOT NULL,
    priority   TEXT NOT NULL DEFAULT 'Normal',
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    fy          TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    billed      REAL NOT NULL DEFAULT 0,
    received    REAL NOT NULL DEFAULT 0,
    date        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_payments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fee_id     INTEGER NOT NULL REFERENCES fees(id) ON DELETE CASCADE,
    amount     REAL NOT NULL,
    date       TEXT NOT NULL,
    mode       TEXT NOT NULL DEFAULT 'Cash',
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fee_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fee_id      INTEGER NOT NULL REFERENCES fees(id) ON DELETE CASCADE,
    category    TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    amount      REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activity (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts   TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS statutory_overrides (
    key      TEXT PRIMARY KEY,
    due_date TEXT NOT NULL,
    title    TEXT NOT NULL DEFAULT '',
    note     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS statutory_custom (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    due_date   TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'ITR',
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

CLIENT_FIELDS = (
    "name", "phone", "email", "aadhar", "pan", "dob", "address", "photo",
    "portal_password", "gst_id", "gst_password", "folder_name", "status", "notes",
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(clients)").fetchall()}
        if "gst_id" not in cols:
            self.conn.execute("ALTER TABLE clients ADD COLUMN gst_id TEXT NOT NULL DEFAULT ''")
        if "gst_password" not in cols:
            self.conn.execute("ALTER TABLE clients ADD COLUMN gst_password TEXT NOT NULL DEFAULT ''")

    def close(self) -> None:
        try:
            self.conn.commit()
            self.conn.close()
        except sqlite3.Error:
            pass

    # ---------------------------------------------------------------- meta
    def get_meta(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row and row["value"] is not None else default

    def set_meta(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self.conn.commit()

    def set_meta_many(self, items: dict[str, str]) -> None:
        for k, v in items.items():
            self.conn.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
        self.conn.commit()

    # ------------------------------------------------------------- clients
    def list_clients(self, search: str = "", status: str = "") -> list[sqlite3.Row]:
        sql = "SELECT * FROM clients WHERE 1=1"
        params: list[Any] = []
        if status and status != "All":
            sql += " AND status=?"
            params.append(status)
        if search.strip():
            like = f"%{search.strip()}%"
            sql += (" AND (name LIKE ? OR pan LIKE ? OR phone LIKE ? OR email LIKE ? "
                    "OR aadhar LIKE ? OR gst_id LIKE ?)")
            params += [like] * 6
        sql += " ORDER BY name COLLATE NOCASE"
        return self.conn.execute(sql, params).fetchall()

    def get_client(self, client_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()

    def pan_exists(self, pan: str, exclude_id: int | None = None) -> bool:
        if not pan:
            return False
        row = self.conn.execute(
            "SELECT id FROM clients WHERE pan=? AND id<>?", (pan, exclude_id or -1)).fetchone()
        return row is not None

    def add_client(self, data: dict[str, Any]) -> int:
        cols = [c for c in CLIENT_FIELDS if c in data]
        cur = self.conn.execute(
            f"INSERT INTO clients({','.join(cols)},created_at) VALUES({','.join('?' * len(cols))},?)",
            [data[c] for c in cols] + [now_iso()])
        self.conn.commit()
        return int(cur.lastrowid)

    def update_client(self, client_id: int, data: dict[str, Any]) -> None:
        cols = [c for c in CLIENT_FIELDS if c in data]
        self.conn.execute(
            f"UPDATE clients SET {','.join(c + '=?' for c in cols)} WHERE id=?",
            [data[c] for c in cols] + [client_id])
        self.conn.commit()

    def delete_client(self, client_id: int) -> None:
        self.conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        self.conn.commit()

    def count_clients(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0])

    def folder_name_taken(self, folder_name: str, exclude_id: int | None = None) -> bool:
        row = self.conn.execute(
            "SELECT id FROM clients WHERE lower(folder_name)=lower(?) AND id<>?",
            (folder_name, exclude_id or -1)).fetchone()
        return row is not None

    # --------------------------------------------------------------- tasks
    def list_tasks(self, include_done: bool = True, client_id: int | None = None) -> list[sqlite3.Row]:
        sql = ("SELECT t.*, c.name AS client_name FROM tasks t "
               "LEFT JOIN clients c ON c.id=t.client_id WHERE 1=1")
        params: list[Any] = []
        if not include_done:
            sql += " AND t.done=0"
        if client_id is not None:
            sql += " AND t.client_id=?"
            params.append(client_id)
        sql += " ORDER BY t.done, t.due_date, t.id"
        return self.conn.execute(sql, params).fetchall()

    def add_task(self, title: str, due_date: str, client_id: int | None, priority: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO tasks(client_id,title,due_date,priority,created_at) VALUES(?,?,?,?,?)",
            (client_id, title, due_date, priority, now_iso()))
        self.conn.commit()
        return int(cur.lastrowid)

    def update_task(self, task_id: int, title: str, due_date: str,
                    client_id: int | None, priority: str) -> None:
        self.conn.execute(
            "UPDATE tasks SET title=?, due_date=?, client_id=?, priority=? WHERE id=?",
            (title, due_date, client_id, priority, task_id))
        self.conn.commit()

    def set_task_done(self, task_id: int, done: bool) -> None:
        self.conn.execute("UPDATE tasks SET done=? WHERE id=?", (1 if done else 0, task_id))
        self.conn.commit()

    def delete_task(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def pending_task_count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM tasks WHERE done=0").fetchone()[0])

    # ---------------------------------------------------------------- fees
    def list_fees(self, client_id: int | None = None) -> list[sqlite3.Row]:
        sql = ("SELECT f.*, c.name AS client_name FROM fees f "
               "JOIN clients c ON c.id=f.client_id")
        params: list[Any] = []
        if client_id is not None:
            sql += " WHERE f.client_id=?"
            params.append(client_id)
        sql += " ORDER BY f.date DESC, f.id DESC"
        return self.conn.execute(sql, params).fetchall()

    def add_fee(self, client_id: int, fy: str, description: str,
                billed: float, received: float, date: str,
                mode: str = "Cash", note: str = "",
                items: list[tuple[str, str, float]] | None = None) -> int:
        ts = now_iso()
        cur = self.conn.execute(
            "INSERT INTO fees(client_id,fy,description,billed,received,date,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (client_id, fy, description, billed, received, date, ts))
        fid = int(cur.lastrowid)
        if items:
            self.conn.executemany(
                "INSERT INTO fee_items(fee_id,category,description,amount) VALUES(?,?,?,?)",
                [(fid, cat, desc, amt) for cat, desc, amt in items])
        if received > 0:
            self.conn.execute(
                "INSERT INTO fee_payments(fee_id,amount,date,mode,note,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (fid, received, date, mode or "Cash", note or "Initial payment", ts))
        self.conn.commit()
        return fid

    def update_fee(self, fee_id: int, client_id: int, fy: str, description: str,
                   billed: float, received: float, date: str,
                   items: list[tuple[str, str, float]] | None = None) -> None:
        self.conn.execute(
            "UPDATE fees SET client_id=?, fy=?, description=?, billed=?, received=?, date=? "
            "WHERE id=?", (client_id, fy, description, billed, received, date, fee_id))
        if items is not None:
            self.conn.execute("DELETE FROM fee_items WHERE fee_id=?", (fee_id,))
            if items:
                self.conn.executemany(
                    "INSERT INTO fee_items(fee_id,category,description,amount) VALUES(?,?,?,?)",
                    [(fee_id, cat, desc, amt) for cat, desc, amt in items])
        self.conn.commit()

    def list_fee_items(self, fee_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM fee_items WHERE fee_id=? ORDER BY id ASC",
            (fee_id,)).fetchall()

    def record_payment(self, fee_id: int, amount: float, pay_date: str,
                       mode: str = "Cash", note: str = "") -> int:
        row = self.conn.execute("SELECT received FROM fees WHERE id=?", (fee_id,)).fetchone()
        if not row:
            raise ValueError("Fee entry not found")
        new_recv = round(float(row["received"]) + amount, 2)
        cur = self.conn.execute(
            "INSERT INTO fee_payments(fee_id,amount,date,mode,note,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (fee_id, amount, pay_date, mode or "Cash", note, now_iso()))
        self.conn.execute("UPDATE fees SET received=? WHERE id=?", (new_recv, fee_id))
        self.conn.commit()
        return int(cur.lastrowid)

    def list_payments(self, fee_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM fee_payments WHERE fee_id=? ORDER BY date ASC, id ASC",
            (fee_id,)).fetchall()

    def client_fee_summary(self, client_id: int, exclude_fee_id: int | None = None) -> tuple[float, float, float]:
        """Return (total_billed, total_received, balance) for a client."""
        if exclude_fee_id is not None:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(billed),0), COALESCE(SUM(received),0) "
                "FROM fees WHERE client_id=? AND id<>?",
                (client_id, exclude_fee_id)).fetchone()
        else:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(billed),0), COALESCE(SUM(received),0) "
                "FROM fees WHERE client_id=?",
                (client_id,)).fetchone()
        billed, recv = float(row[0]), float(row[1])
        return billed, recv, round(billed - recv, 2)

    def get_fee(self, fee_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT f.*, c.name AS client_name, c.pan AS client_pan, "
            "c.phone AS client_phone, c.email AS client_email, c.address AS client_address "
            "FROM fees f JOIN clients c ON c.id=f.client_id WHERE f.id=?",
            (fee_id,)).fetchone()

    def delete_fee(self, fee_id: int) -> None:
        self.conn.execute("DELETE FROM fees WHERE id=?", (fee_id,))
        self.conn.commit()

    def fee_totals(self) -> tuple[float, float]:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(billed),0), COALESCE(SUM(received),0) FROM fees").fetchone()
        return float(row[0]), float(row[1])

    # ------------------------------------------------------------ activity
    def log(self, text: str) -> None:
        self.conn.execute("INSERT INTO activity(ts,text) VALUES(?,?)", (now_iso(), text))
        self.conn.execute(
            "DELETE FROM activity WHERE id NOT IN (SELECT id FROM activity ORDER BY id DESC LIMIT 200)")
        self.conn.commit()

    def recent_activity(self, limit: int = 8) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    # ------------------------------------------------- statutory overrides
    def statutory_overrides(self) -> dict[str, sqlite3.Row]:
        rows = self.conn.execute("SELECT * FROM statutory_overrides").fetchall()
        return {r["key"]: r for r in rows}

    def set_statutory_override(self, key: str, due_date: str, title: str = "", note: str = "") -> None:
        self.conn.execute(
            "INSERT INTO statutory_overrides(key,due_date,title,note) VALUES(?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET due_date=excluded.due_date, "
            "title=excluded.title, note=excluded.note",
            (key, due_date, title, note))
        self.conn.commit()

    def clear_statutory_override(self, key: str) -> None:
        self.conn.execute("DELETE FROM statutory_overrides WHERE key=?", (key,))
        self.conn.commit()

    # ------------------------------------------------- manual statutory dates
    def list_custom_statutory(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM statutory_custom ORDER BY due_date, id").fetchall()

    def add_custom_statutory(self, title: str, due_date: str,
                             kind: str = "ITR", note: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO statutory_custom(title,due_date,kind,note,created_at) VALUES(?,?,?,?,?)",
            (title, due_date, kind, note, now_iso()))
        self.conn.commit()
        return int(cur.lastrowid)

    def update_custom_statutory(self, custom_id: int, title: str, due_date: str,
                                kind: str = "ITR", note: str = "") -> None:
        self.conn.execute(
            "UPDATE statutory_custom SET title=?, due_date=?, kind=?, note=? WHERE id=?",
            (title, due_date, kind, note, custom_id))
        self.conn.commit()

    def delete_custom_statutory(self, custom_id: int) -> None:
        self.conn.execute("DELETE FROM statutory_custom WHERE id=?", (custom_id,))
        self.conn.commit()
