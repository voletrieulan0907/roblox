#!/usr/bin/env python
"""Initialize database tables"""
import sqlite3
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rbx_sessions.db')

def init_db():
    """Create database tables"""
    conn = sqlite3.connect(DB_PATH)
    
    # Drop old tables if they exist (for fresh start)
    # conn.execute("DROP TABLE IF EXISTS auth")
    # conn.execute("DROP TABLE IF EXISTS sessions")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT UNIQUE NOT NULL,
            cookie TEXT NOT NULL,
            previousCookie TEXT DEFAULT '',
            username TEXT DEFAULT '',
            displayName TEXT DEFAULT '',
            userAgent TEXT DEFAULT '',
            status TEXT DEFAULT 'ALIVE' CHECK(status IN ('ALIVE','PAUSED','DIE')),
            messageId TEXT DEFAULT '',
            game TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            refreshCount INTEGER DEFAULT 0,
            createdAt TEXT DEFAULT (datetime('now')),
            updatedAt TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS auth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT UNIQUE NOT NULL,
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            createdAt TEXT DEFAULT (datetime('now')),
            updatedAt TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (userId) REFERENCES sessions(userId)
        );
    """)
    conn.commit()
    
    # Migration: add columns if they don't exist
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN previousCookie TEXT DEFAULT ''")
        conn.commit()
    except:
        pass
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN refreshCount INTEGER DEFAULT 0")
        conn.commit()
    except:
        pass
    
    conn.close()
    print(f"✅ Database initialized at: {DB_PATH}")

if __name__ == '__main__':
    init_db()
