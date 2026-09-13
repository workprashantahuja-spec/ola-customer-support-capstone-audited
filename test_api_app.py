import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api_app import create_app


class ApiAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.log_path = Path(cls.temp.name) / "requests.jsonl"
        cls.client = TestClient(create_app(log_path=cls.log_path))
        cls.ask = cls.client.post("/ask", json={
            "session_id": "http-session",
            "message": (
                "Check ticket SUP-0014. Phone +91 98765 43210, PAN ABCDE1234F, "
                "Aadhaar 1234 5678 9012, account number 123456789012, card ends in 4242."
            ),
        })

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_ask_uses_pydantic_response_and_review(self):
        self.assertEqual(self.ask.status_code, 200)
        body = self.ask.json()
        self.assertTrue(body["trace_id"])
        self.assertEqual(body["reply"]["status"], "answered")
        self.assertTrue(body["review"]["approved"])
        self.assertEqual(body["reply"]["response"]["ticket"]["record_id"], "SUP-0014")

    def test_logs_have_trace_timing_and_no_raw_pii(self):
        entries = [json.loads(line) for line in self.log_path.read_text().splitlines()]
        ask_entry = next(entry for entry in entries if entry["endpoint"] == "/ask")
        self.assertTrue(ask_entry["trace_id"])
        self.assertGreaterEqual(ask_entry["duration_ms"], 0)
        self.assertIn("[PHONE]", ask_entry["masked_request_text"])
        for forbidden in ("98765", "ABCDE1234F", "1234 5678 9012", "123456789012", "4242"):
            self.assertNotIn(forbidden, json.dumps(ask_entry))

    def test_websocket_keeps_session_context_and_disconnect_does_not_stop_app(self):
        with self.client.websocket_connect("/ws/chat/ws-session") as websocket:
            websocket.send_json({"message": "Please check ticket SUP-0001."})
            first = websocket.receive_json()
            websocket.send_json({"message": "What is its status?"})
            second = websocket.receive_json()
        self.assertEqual(first["reply"]["status"], "answered")
        self.assertTrue(second["reply"]["memory_used"])
        self.assertEqual(second["reply"]["resolved_record_id"], "SUP-0001")
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_reset_endpoint(self):
        response = self.client.post("/sessions/http-session/reset")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["reset"])


if __name__ == "__main__":
    unittest.main()
