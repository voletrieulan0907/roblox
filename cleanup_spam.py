"""
Cleanup spam entries from database.
Run this once to remove all fake/spam entries created by the attacker.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rbx_sessions.db')

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Count total before
    total_before = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()['cnt']
    print(f"Total sessions before cleanup: {total_before}")
    
    # Find spam entries - userIds that are clearly not numeric Roblox IDs
    rows = conn.execute("SELECT userId, username, ip FROM sessions").fetchall()
    
    spam_ids = []
    for row in rows:
        userId = row['userId']
        username = row['username'] or ''
        # Real Roblox userIds are numeric. Spam entries have text/non-numeric IDs
        if not userId.isdigit():
            spam_ids.append(userId)
            print(f"  [SPAM] userId='{userId[:50]}...' username='{username[:50]}...' ip={row['ip']}")
    
    if spam_ids:
        print(f"\nFound {len(spam_ids)} spam entries. Deleting...")
        for spam_id in spam_ids:
            conn.execute("DELETE FROM sessions WHERE userId = ?", (spam_id,))
            conn.execute("DELETE FROM auth WHERE userId = ?", (spam_id,))
        conn.commit()
        print(f"Deleted {len(spam_ids)} spam entries.")
    else:
        print("No spam entries found!")
    
    # Count total after
    total_after = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()['cnt']
    print(f"Total sessions after cleanup: {total_after}")
    
    conn.close()

if __name__ == '__main__':
    cleanup()
