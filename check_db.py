"""Check database status"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), 'rbx_sessions.db')

if not os.path.exists(DB):
    print("Database not found!")
    exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=" * 60)
print("  RBX SESSION DATABASE STATUS")
print("=" * 60)

rows = conn.execute("SELECT * FROM sessions ORDER BY updatedAt DESC").fetchall()

for r in rows:
    status = r['status']
    icon = {'ALIVE': '[OK]', 'DIE': '[X]', 'PAUSED': '[--]'}.get(status, '[?]')
    cookie_len = len(r['cookie']) if r['cookie'] else 0
    print(f"\n  {icon} {r['username']} ({r['userId']})")
    print(f"      Status:  {status}")
    print(f"      Game:    {r['game']}")
    print(f"      Cookie:  {cookie_len} chars")
    print(f"      Updated: {r['updatedAt']}")
    print(f"      Created: {r['createdAt']}")

print(f"\n{'=' * 60}")

# Count by status
for st in ['ALIVE', 'DIE', 'PAUSED']:
    cnt = conn.execute("SELECT COUNT(*) FROM sessions WHERE status=?", (st,)).fetchone()[0]
    print(f"  {st}: {cnt}")

total = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
print(f"  TOTAL: {total}")
print("=" * 60)

conn.close()
