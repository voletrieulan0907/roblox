#!/usr/bin/env python
"""Restore account from old data or add new test account"""
import sqlite3
import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rbx_sessions.db')

def restore_account():
    """Add test account to database"""
    conn = sqlite3.connect(DB_PATH)
    
    # Account data from old screenshot
    userId = '11154590723'
    username = 'helloacctest121'
    cookie = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_TEST_COOKIE_DATA'
    game = 'Jailbreak'
    status = 'ALIVE'
    now = datetime.now(timezone.utc).isoformat()
    
    try:
        conn.execute("""
            INSERT INTO sessions (userId, cookie, username, game, status, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (userId, cookie, username, game, status, now, now))
        conn.commit()
        print(f"✅ Account restored: {username} ({userId})")
    except sqlite3.IntegrityError:
        print(f"⚠️ Account already exists: {username}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    restore_account()
