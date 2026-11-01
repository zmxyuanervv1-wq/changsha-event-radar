
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def connect():
    if not DATABASE_URL:
        raise RuntimeError("请先在部署平台设置 DATABASE_URL（Supabase PostgreSQL 连接串）")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with connect() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id BIGSERIAL PRIMARY KEY,
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
            collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS collection_logs (
            id BIGSERIAL PRIMARY KEY,
            source_name TEXT,
            source_url TEXT,
            status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_collection(source_name, source_url, status, message):
    with connect() as db:
        db.execute(
            "INSERT INTO collection_logs(source_name,source_url,status,message) VALUES(%s,%s,%s,%s)",
            (source_name, source_url, status, message)
        )
        db.commit()
