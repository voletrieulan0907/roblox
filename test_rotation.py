"""
Test Cookie Rotation - Verify the nurturing mechanism works
This script manually rotates the cookie to prove the refresh logic is functional.
"""
import sqlite3
import requests
import os
import sys

DB = os.path.join(os.path.dirname(__file__), 'rbx_sessions.db')
ROBLOX_AUTH_URL = "https://auth.roblox.com/v1/authentication-ticket"
ROBLOX_REDEEM_URL = "https://auth.roblox.com/v1/authentication-ticket/redeem"
ROBLOX_USER_URL = "https://users.roblox.com/v1/users/authenticated"

def get_session_from_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM sessions WHERE status='ALIVE' LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None

def verify_cookie(cookie):
    """Check if a cookie is valid by calling Roblox API"""
    try:
        resp = requests.get(
            ROBLOX_USER_URL,
            headers={'Cookie': f'.ROBLOSECURITY={cookie}'},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return True, data.get('name', '?'), data.get('id', '?')
        return False, None, None
    except Exception as e:
        return False, None, str(e)

def rotate_cookie(old_cookie):
    """Full rotation: old cookie -> new cookie"""
    headers = {
        'Cookie': f'.ROBLOSECURITY={old_cookie}',
        'Content-Type': 'application/json',
        'Referer': 'https://www.roblox.com'
    }

    # Step A: Get CSRF token
    print("  [A] Getting CSRF token...")
    resp_a = requests.post(ROBLOX_AUTH_URL, headers=headers, timeout=10)
    csrf = resp_a.headers.get('x-csrf-token')
    if not csrf:
        print(f"  [A] FAILED - No CSRF token (status: {resp_a.status_code})")
        return None
    print(f"  [A] OK - CSRF: {csrf[:20]}...")

    # Step B: Get auth ticket
    print("  [B] Getting auth ticket...")
    headers['x-csrf-token'] = csrf
    resp_b = requests.post(ROBLOX_AUTH_URL, headers=headers, timeout=10)
    ticket = resp_b.headers.get('rbx-authentication-ticket')
    if not ticket:
        print(f"  [B] FAILED - No ticket (status: {resp_b.status_code})")
        return None
    print(f"  [B] OK - Ticket: {ticket[:30]}...")

    # Step C: Redeem ticket for new cookie
    print("  [C] Redeeming ticket...")
    redeem_headers = {
        'Content-Type': 'application/json',
        'RBXAuthenticationNegotiation': '1',
    }
    resp_c = requests.post(
        ROBLOX_REDEEM_URL,
        headers=redeem_headers,
        json={'authenticationTicket': ticket},
        timeout=10
    )
    
    set_cookie = resp_c.headers.get('set-cookie', '')
    new_cookie = None
    for part in set_cookie.split(','):
        if '.ROBLOSECURITY=' in part:
            val = part.split('.ROBLOSECURITY=')[1].split(';')[0].strip()
            if val and len(val) > 50:
                new_cookie = val
                break
    
    if new_cookie:
        print(f"  [C] OK - New cookie: {new_cookie[:40]}... ({len(new_cookie)} chars)")
        return new_cookie
    else:
        print(f"  [C] FAILED - No cookie in response (status: {resp_c.status_code})")
        return None

def update_db(userId, new_cookie):
    from datetime import datetime, timezone
    conn = sqlite3.connect(DB)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE sessions SET cookie=?, updatedAt=? WHERE userId=?", (new_cookie, now, userId))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  COOKIE ROTATION TEST")
    print("=" * 60)

    # Step 1: Get session from DB
    session = get_session_from_db()
    if not session:
        print("\nNo ALIVE sessions in database!")
        sys.exit(1)
    
    print(f"\n[1] Session found: {session['username']} ({session['userId']})")
    print(f"    Status: {session['status']}")
    print(f"    Old cookie: {session['cookie'][:40]}... ({len(session['cookie'])} chars)")

    # Step 2: Verify old cookie still works
    print(f"\n[2] Verifying old cookie...")
    valid, name, uid = verify_cookie(session['cookie'])
    if valid:
        print(f"    OLD COOKIE VALID - User: {name} (ID: {uid})")
    else:
        print(f"    OLD COOKIE INVALID - rotation will fail")
        sys.exit(1)

    # Step 3: Rotate cookie
    print(f"\n[3] Rotating cookie (3-step process)...")
    new_cookie = rotate_cookie(session['cookie'])
    
    if not new_cookie:
        print(f"\n    ROTATION FAILED!")
        sys.exit(1)
    
    # Step 4: Verify new cookie works
    print(f"\n[4] Verifying NEW cookie...")
    valid2, name2, uid2 = verify_cookie(new_cookie)
    if valid2:
        print(f"    NEW COOKIE VALID - User: {name2} (ID: {uid2})")
    else:
        print(f"    NEW COOKIE INVALID!")
        sys.exit(1)

    # Step 5: Check old cookie is now invalid
    print(f"\n[5] Checking old cookie (should be invalidated)...")
    old_valid, _, _ = verify_cookie(session['cookie'])
    if old_valid:
        print(f"    Old cookie still valid (Roblox may keep both active briefly)")
    else:
        print(f"    Old cookie INVALIDATED - rotation took over the account!")

    # Step 6: Save new cookie to DB
    print(f"\n[6] Saving new cookie to database...")
    update_db(session['userId'], new_cookie)
    print(f"    Database updated!")

    print(f"\n{'=' * 60}")
    print(f"  ROTATION TEST: PASSED!")
    print(f"  Old cookie ({len(session['cookie'])} chars) -> New cookie ({len(new_cookie)} chars)")
    print(f"  Account {session['username']} will stay ALIVE!")
    print(f"{'=' * 60}")
