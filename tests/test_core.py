from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nightbounty.crypto import decrypt_report, encrypt_report
from nightbounty import store


class NightBountyCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = store.DATABASE_PATH
        store.DATABASE_PATH = Path(self.temp_dir.name) / "nightbounty-test.db"
        store.initialize()

    def tearDown(self) -> None:
        store.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_encrypted_payload_requires_correct_collaboration_key(self) -> None:
        payload = {"report_title": "Stored XSS", "impact": "Session compromise"}
        encrypted = encrypt_report(payload, "owner-demo-key")

        self.assertNotIn("Stored XSS", encrypted["ciphertext"])
        self.assertEqual(
            decrypt_report(encrypted["ciphertext"], encrypted["encryption_salt"], "owner-demo-key"),
            payload,
        )
        with self.assertRaises(ValueError):
            decrypt_report(encrypted["ciphertext"], encrypted["encryption_salt"], "incorrect-key")

    def test_first_report_lifecycle_is_enforced(self) -> None:
        encrypted = encrypt_report({"proof": "safe demo"}, "owner-demo-key")
        report = store.submit_report(
            bounty_id="BNTY-MDN-01",
            reporter_alias="nocturne_17",
            report_title="Stored XSS",
            severity="Critical",
            ciphertext=encrypted["ciphertext"],
            encryption_salt=encrypted["encryption_salt"],
            commitment=encrypted["commitment"],
            payload_digest=encrypted["payload_digest"],
            chain_status="LOCAL_COMMITMENT",
        )
        self.assertEqual(report["status"], "SUBMITTED")
        self.assertEqual(store.get_bounty()["status"], "REPORT_SUBMITTED")

        with self.assertRaises(ValueError):
            store.submit_report(
                bounty_id="BNTY-MDN-01",
                reporter_alias="second_researcher",
                report_title="Second report",
                severity="High",
                ciphertext=encrypted["ciphertext"],
                encryption_salt=encrypted["encryption_salt"],
                commitment=encrypted["commitment"],
                payload_digest=encrypted["payload_digest"],
                chain_status="LOCAL_COMMITMENT",
            )

        store.transition_report(report["id"], "ACCEPTED", chain_status="LOCAL_OWNER_ACTION")
        store.transition_report(
            report["id"],
            "PAID",
            chain_status="LOCAL_PAYOUT_RECEIPT",
            payout_reference="shielded-demo-receipt",
        )
        updated = store.get_report(report["id"])
        self.assertEqual(updated["status"], "PAID")
        self.assertEqual(updated["payout_reference"], "shielded-demo-receipt")
        self.assertEqual(store.metrics()["paid"], 1)


if __name__ == "__main__":
    unittest.main()
