from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nightbounty import store
from nightbounty.access import matches_owner_access_code, normalize_owner_access_code
from nightbounty.crypto import (
    decrypt_report,
    encrypt_report,
    generate_owner_keypair,
    is_public_key_envelope,
)


class NightBountyCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = store.DATABASE_PATH
        store.DATABASE_PATH = Path(self.temp_dir.name) / "nightbounty-test.db"
        store.initialize()
        self.owner_keypair = generate_owner_keypair()

    def tearDown(self) -> None:
        store.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_owner_gate_rejects_missing_placeholder_and_incorrect_codes(self) -> None:
        configured = normalize_owner_access_code("correct-owner-code-2026")

        self.assertEqual(configured, "correct-owner-code-2026")
        self.assertIsNone(normalize_owner_access_code("too-short"))
        self.assertIsNone(normalize_owner_access_code("replace-with-a-long-random-owner-code"))
        self.assertTrue(matches_owner_access_code("correct-owner-code-2026", configured))
        self.assertFalse(matches_owner_access_code("incorrect-owner-code", configured))
        self.assertFalse(matches_owner_access_code("correct-owner-code-2026", None))

    def test_public_key_envelope_requires_the_owner_key_and_correct_bounty(self) -> None:
        payload = {"report_title": "Stored XSS", "impact": "Session compromise"}
        encrypted = encrypt_report(
            payload,
            self.owner_keypair["public_key_b64"],
            bounty_id="BNTY-MDN-01",
        )
        second_encrypted = encrypt_report(
            payload,
            self.owner_keypair["public_key_b64"],
            bounty_id="BNTY-MDN-01",
        )

        self.assertNotIn("Stored XSS", encrypted["ciphertext"])
        self.assertTrue(is_public_key_envelope(encrypted["encryption_salt"]))
        self.assertNotEqual(encrypted["ciphertext"], second_encrypted["ciphertext"])
        self.assertNotEqual(encrypted["encryption_salt"], second_encrypted["encryption_salt"])
        self.assertEqual(
            decrypt_report(
                encrypted["ciphertext"],
                encrypted["encryption_salt"],
                self.owner_keypair["private_key_b64"],
                bounty_id="BNTY-MDN-01",
            ),
            payload,
        )
        with self.assertRaises(ValueError):
            decrypt_report(
                encrypted["ciphertext"],
                encrypted["encryption_salt"],
                generate_owner_keypair()["private_key_b64"],
                bounty_id="BNTY-MDN-01",
            )
        with self.assertRaises(ValueError):
            decrypt_report(
                encrypted["ciphertext"],
                encrypted["encryption_salt"],
                self.owner_keypair["private_key_b64"],
                bounty_id="BNTY-MDN-02",
            )
        with self.assertRaises(ValueError):
            decrypt_report(
                encrypted["ciphertext"][:-1] + "A",
                encrypted["encryption_salt"],
                self.owner_keypair["private_key_b64"],
                bounty_id="BNTY-MDN-01",
            )

    def create_demo_bounty(self, title: str) -> dict[str, object]:
        return store.create_bounty(
            title=title,
            target_name="AstraCMS · isolated staging target",
            reward="150 tNIGHT",
            severity="High",
            description="A safe, isolated demo scenario for responsible testing.",
            scope="Only the supplied staging URL and test accounts.",
            owner_alias="AstraCMS Security Desk",
        )

    def test_multiple_bounties_are_isolated(self) -> None:
        first_bounty = self.create_demo_bounty("Unsafe attachment preview")
        second_bounty = self.create_demo_bounty("Misconfigured export endpoint")
        self.assertNotEqual(first_bounty["id"], second_bounty["id"])
        self.assertEqual(first_bounty["status"], "OPEN")
        self.assertEqual(second_bounty["status"], "OPEN")
        self.assertEqual(len(store.list_events(str(first_bounty["id"]))), 1)
        self.assertEqual(len(store.list_events(str(second_bounty["id"]))), 1)
        self.assertEqual(store.metrics()["open_bounties"], 3)

        first_encrypted = encrypt_report(
            {"proof": "safe demo"},
            self.owner_keypair["public_key_b64"],
            bounty_id=str(first_bounty["id"]),
        )
        second_encrypted = encrypt_report(
            {"proof": "safe demo"},
            self.owner_keypair["public_key_b64"],
            bounty_id=str(second_bounty["id"]),
        )
        first_report = store.submit_report(
            bounty_id=str(first_bounty["id"]),
            reporter_alias="nocturne_17",
            report_title="Unsafe attachment preview",
            severity="High",
            ciphertext=first_encrypted["ciphertext"],
            encryption_salt=first_encrypted["encryption_salt"],
            commitment=first_encrypted["commitment"],
            payload_digest=first_encrypted["payload_digest"],
            chain_status="LOCAL_DEMO_COMMITMENT",
        )
        second_report = store.submit_report(
            bounty_id=str(second_bounty["id"]),
            reporter_alias="another_researcher",
            report_title="Export authorization gap",
            severity="Medium",
            ciphertext=second_encrypted["ciphertext"],
            encryption_salt=second_encrypted["encryption_salt"],
            commitment=second_encrypted["commitment"],
            payload_digest=second_encrypted["payload_digest"],
            chain_status="LOCAL_DEMO_COMMITMENT",
        )
        self.assertEqual(first_report["status"], "SUBMITTED")
        self.assertEqual(second_report["status"], "SUBMITTED")
        self.assertEqual([report["id"] for report in store.list_reports(str(first_bounty["id"]))], [first_report["id"]])
        self.assertEqual([report["id"] for report in store.list_reports(str(second_bounty["id"]))], [second_report["id"]])
        self.assertTrue(all(event["bounty_id"] == first_bounty["id"] for event in store.list_events(str(first_bounty["id"]))))

        with self.assertRaises(ValueError):
            store.submit_report(
                bounty_id=str(first_bounty["id"]),
                reporter_alias="second_researcher",
                report_title="Duplicate report",
                severity="High",
                ciphertext=first_encrypted["ciphertext"],
                encryption_salt=first_encrypted["encryption_salt"],
                commitment=first_encrypted["commitment"],
                payload_digest=first_encrypted["payload_digest"],
                chain_status="LOCAL_DEMO_COMMITMENT",
            )

        store.transition_report(first_report["id"], "ACCEPTED", chain_status="LOCAL_DEMO_OWNER_ACTION")
        store.transition_report(
            first_report["id"],
            "PAID",
            chain_status="LOCAL_DEMO_PAYOUT_RECEIPT",
            payout_reference="shielded-demo-receipt",
        )
        updated = store.get_report(first_report["id"])
        assert updated is not None
        self.assertEqual(updated["status"], "PAID")
        self.assertEqual(updated["payout_reference"], "shielded-demo-receipt")
        self.assertEqual(store.metrics(), {"open_bounties": 1, "private_reports": 2, "resolved": 1, "paid": 1})


if __name__ == "__main__":
    unittest.main()
