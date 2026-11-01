import sqlite3
from pathlib import Path

import os
DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "events.db")))

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '其他',
            description TEXT DEFAULT '',
            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',
            venue TEXT DEFAULT '',
            price TEXT DEFAULT '待确认',
            image_url TEXT DEFAULT '',
            signup_url TEXT DEFAULT '',
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL UNIQUE,
            verification TEXT NOT NULL DEFAULT '待核实',
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS collection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            source_url TEXT,
            status TEXT,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_collection(source_name, source_url, status, message):
    with connect() as db:
        db.execute("INSERT INTO collection_logs(source_name,source_url,status,message) VALUES(?,?,?,?)",
                   (source_name, source_url, status, message))
        db.commit()
