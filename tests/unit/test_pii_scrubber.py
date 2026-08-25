"""Unit tests for PII and credential redaction engine."""

from __future__ import annotations

import unittest
from src.observability.pii_scrubber import PIIScrubber, scrub_dict, scrub_text


class TestPIIScrubber(unittest.TestCase):
    """Test cases verifying PII Redaction."""

    def test_email_redaction(self):
        text = "Contact engineer alice.smith@example.com for incident handoff."
        clean = scrub_text(text)
        self.assertNotIn("alice.smith@example.com", clean)
        self.assertIn("[REDACTED_EMAIL]", clean)

    def test_ip_address_redaction(self):
        text = "Traffic flood detected from IP 198.51.100.42 targeting port 443."
        clean = scrub_text(text)
        self.assertNotIn("198.51.100.42", clean)
        self.assertIn("[REDACTED_IP]", clean)

    def test_api_key_and_jwt_redaction(self):
        sample_key = "".join(["AIza", "SyA12345678901234567890123456789012"])
        sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakSignature"
        text = f"Key: {sample_key} and Auth: Bearer {sample_jwt}"
        clean = scrub_text(text)
        self.assertNotIn(sample_key, clean)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", clean)
        self.assertIn("[REDACTED_GOOGLE_API_KEY]", clean)
        self.assertIn("[REDACTED_JWT_TOKEN]", clean)

    def test_dictionary_redaction(self):
        sample_token = "".join(["sk-", "supersecret12345678901234567890"])
        payload = {
            "service": "auth-service",
            "api_key": sample_token,
            "nested": {
                "admin_email": "ops-lead@google.com",
                "client_ip": "203.0.113.19",
            },
        }
        scrubbed = scrub_dict(payload)
        self.assertEqual(scrubbed["api_key"], "[REDACTED_CREDENTIAL]")
        self.assertEqual(scrubbed["nested"]["admin_email"], "[REDACTED_EMAIL]")
        self.assertEqual(scrubbed["nested"]["client_ip"], "[REDACTED_IP]")


if __name__ == "__main__":
    unittest.main()
