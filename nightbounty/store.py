"""SQLite persistence for the NightBounty hackathon MVP."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("NIGHTBOUNTY_DB", ROOT / "nightbounty.db"))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS bounties (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                target_name TEXT NOT NULL,
                reward TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                scope TEXT NOT NULL,
                owner_alias TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                bounty_id TEXT NOT NULL,
                reporter_alias TEXT NOT NULL,
                report_title TEXT NOT NULL,
                severity TEXT NOT NULL,
                ciphertext TEXT NOT NULL,
                encryption_salt TEXT NOT NULL,
                commitment TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                status TEXT NOT NULL,
                payout_reference TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                FOREIGN KEY (bounty_id) REFERENCES bounties(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                bounty_id TEXT NOT NULL,
                report_id TEXT,
                event_type TEXT NOT NULL,
                public_summary TEXT NOT NULL,
                private_note TEXT,
                chain_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (bounty_id) REFERENCES bounties(id),
                FOREIGN KEY (report_id) REFERENCES reports(id)
            );
            """
        )
    seed_demo_data()


def seed_demo_data() -> None:
    """Create one narrow, intentionally safe bounty for the demo storyline."""
    with connection() as conn:
        existing = conn.execute("SELECT id FROM bounties WHERE id = ?", ("BNTY-MDN-01",)).fetchone()
        if existing:
            return

        timestamp = now()
        conn.execute(
            """
            INSERT INTO bounties (
                id, title, target_name, reward, severity, description, scope,
                owner_alias, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "BNTY-MDN-01",
                "Stored XSS in AstraCMS editor",
                "AstraCMS · isolated staging target",
                "250 tNIGHT",
                "Critical",
                "A deliberately vulnerable staging editor is available for responsible testing. "
                "The winning researcher receives a shielded reward after private review.",
                "Only https://staging.astracms.demo/editor using supplied test accounts. "
                "No production systems, data extraction, or denial-of-service testing.",
                "AstraCMS security desk",
                "OPEN",
                timestamp,
            ),
        )
        _add_event(
            conn,
            bounty_id="BNTY-MDN-01",
            report_id=None,
            event_type="BOUNTY_OPENED",
            public_summary="Bounty opened for private responsible disclosure.",
            private_note=None,
            chain_status="PREPROD_REQUIRED",
        )


def _add_event(
    conn: sqlite3.Connection,
    *,
    bounty_id: str,
    report_id: str | None,
    event_type: str,
    public_summary: str,
    private_note: str | None,
    chain_status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO events (
            id, bounty_id, report_id, event_type, public_summary,
            private_note, chain_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"EVT-{uuid.uuid4().hex[:10].upper()}",
            bounty_id,
            report_id,
            event_type,
            public_summary,
            private_note,
            chain_status,
            now(),
        ),
    )


def get_bounty(bounty_id: str = "BNTY-MDN-01") -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
    return dict(row) if row else None


def list_bounties() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT * FROM bounties ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def submit_report(
    *,
    bounty_id: str,
    reporter_alias: str,
    report_title: str,
    severity: str,
    ciphertext: str,
    encryption_salt: str,
    commitment: str,
    payload_digest: str,
    chain_status: str,
) -> dict[str, Any]:
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    with connection() as conn:
        bounty = conn.execute("SELECT status FROM bounties WHERE id = ?", (bounty_id,)).fetchone()
        if bounty is None:
            raise ValueError("Bounty not found.")
        if bounty["status"] != "OPEN":
            raise ValueError("This single-case bounty already has a private report in progress.")

        conn.execute(
            """
            INSERT INTO reports (
                id, bounty_id, reporter_alias, report_title, severity, ciphertext,
                encryption_salt, commitment, payload_digest, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                bounty_id,
                reporter_alias.strip(),
                report_title.strip(),
                severity,
                ciphertext,
                encryption_salt,
                commitment,
                payload_digest,
                "SUBMITTED",
                now(),
            ),
        )
        conn.execute("UPDATE bounties SET status = ? WHERE id = ?", ("REPORT_SUBMITTED", bounty_id))
        _add_event(
            conn,
            bounty_id=bounty_id,
            report_id=report_id,
            event_type="PRIVATE_REPORT_COMMITTED",
            public_summary="A private report commitment was recorded. Exploit details remain encrypted.",
            private_note="Ciphertext and private report metadata stored locally for owner review.",
            chain_status=chain_status,
        )
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return dict(row)


def list_reports(bounty_id: str = "BNTY-MDN-01") -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reports WHERE bounty_id = ? ORDER BY created_at DESC", (bounty_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_report(report_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return dict(row) if row else None


def transition_report(
    report_id: str,
    next_status: str,
    *,
    chain_status: str,
    payout_reference: str | None = None,
) -> None:
    allowed = {
        "SUBMITTED": {"ACCEPTED", "REJECTED"},
        "ACCEPTED": {"PAID"},
        "REJECTED": set(),
        "PAID": set(),
    }
    with connection() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if report is None:
            raise ValueError("Report not found.")
        current_status = report["status"]
        if next_status not in allowed.get(current_status, set()):
            raise ValueError(f"Cannot move a {current_status.lower()} report to {next_status.lower()}.")

        reviewed_at = now()
        conn.execute(
            """
            UPDATE reports
            SET status = ?, reviewed_at = ?, payout_reference = COALESCE(?, payout_reference)
            WHERE id = ?
            """,
            (next_status, reviewed_at, payout_reference.strip() if payout_reference else None, report_id),
        )
        conn.execute("UPDATE bounties SET status = ? WHERE id = ?", (next_status, report["bounty_id"]))

        messages = {
            "ACCEPTED": "Owner accepted the private report. Reward authorization is now available.",
            "REJECTED": "Owner closed a private report without public disclosure.",
            "PAID": "Shielded reward marked as paid. The public record contains no recipient identity.",
        }
        _add_event(
            conn,
            bounty_id=report["bounty_id"],
            report_id=report_id,
            event_type=f"REPORT_{next_status}",
            public_summary=messages[next_status],
            private_note="Owner action recorded in the NightBounty case lifecycle.",
            chain_status=chain_status,
        )


def list_events(bounty_id: str = "BNTY-MDN-01", limit: int = 12) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM events WHERE bounty_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (bounty_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def metrics() -> dict[str, int]:
    with connection() as conn:
        report_count = conn.execute("SELECT COUNT(*) AS total FROM reports").fetchone()["total"]
        resolved_count = conn.execute(
            "SELECT COUNT(*) AS total FROM reports WHERE status IN ('ACCEPTED', 'PAID')"
        ).fetchone()["total"]
        paid_count = conn.execute("SELECT COUNT(*) AS total FROM reports WHERE status = 'PAID'").fetchone()["total"]
    return {
        "open_bounties": 1,
        "private_reports": int(report_count),
        "resolved": int(resolved_count),
        "paid": int(paid_count),
    }


def reset_demo_data() -> None:
    with connection() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM reports")
        conn.execute("DELETE FROM bounties")
    seed_demo_data()
