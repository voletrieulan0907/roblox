"""Quick test to verify Discord webhook URL works"""
import requests
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')
print(f"Webhook URL: {WEBHOOK_URL[:60]}...")

if not WEBHOOK_URL:
    print("ERROR: No webhook URL found in .env!")
    exit(1)

payload = {
    "embeds": [{
        "title": "TEST - Webhook Working!",
        "description": "If you see this, the webhook is configured correctly.",
        "color": 0x10b981,
        "fields": [
            {"name": "Status", "value": "OK", "inline": True},
            {"name": "Source", "value": "test_webhook.py", "inline": True}
        ]
    }]
}

resp = requests.post(f"{WEBHOOK_URL}?wait=true", json=payload)
print(f"Response: {resp.status_code}")
print(f"Body: {resp.text[:200]}")

if resp.status_code == 200:
    print("\nSUCCESS! Webhook is working. Check Discord channel.")
else:
    print(f"\nFAILED! Status: {resp.status_code}")
    print(f"Error: {resp.text}")
