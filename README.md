# NightBounty

> **Find bugs. Prove first. Get paid. Stay private.**

NightBounty is a privacy-first responsible-disclosure workflow for Midnight. A security researcher encrypts a report, commits a salted proof of submission, and receives a shielded tNIGHT reward after the bounty owner accepts the issue. The public dashboard shows only safe lifecycle signals—not exploit content or researcher identity.

![NightBounty flow](https://img.shields.io/badge/Midnight-PreProd%20ready-2DE1C2?style=flat-square)

## Why Midnight

A vulnerability report is exactly the kind of data that should **not** be placed on a conventional public blockchain. The report can contain exploit paths, proof-of-concept payloads, vulnerable URLs, and identifying details about the researcher.

| Public / auditable | Private by design |
| --- | --- |
| Contract deployment and bounty state | Raw vulnerability report |
| Report/payout commitments | Reporter pseudonym |
| Safe resolution status | Report salt and decryption key |
| Redacted advisory after a fix | Shielded payout recipient |

## Solo-hackathon MVP

The Streamlit workspace lets one authorized organization publish several **local demo bounties**. Each bounty independently follows one focused, private first-report lifecycle:

```text
OPEN → REPORT_SUBMITTED → ACCEPTED / REJECTED → PAID
```

This is deliberately a multi-bounty workspace for one owner—not a public multi-organization marketplace. The Compact source remains one deployed bounty lifecycle per contract instance; locally published demo bounties are clearly marked as local and are not presented as separate on-chain deployments.

## Run the Streamlit app

### Prerequisites

- Python 3.10+
- Streamlit
- `cryptography`

### Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints. The SQLite database is created automatically as `nightbounty.db`; it is ignored by Git.

### Owner-console access

The public dashboard is intentionally viewable by everyone, but report metadata, ciphertext, decryption, and lifecycle decisions are behind an owner gate.

Set a long, private access code by **one** of these methods before opening **Owner Console**:

```bash
export NIGHTBOUNTY_OWNER_ACCESS_CODE="your-long-random-owner-code"
streamlit run app.py
```

Or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace its example value. For Streamlit Community Cloud, add this in **App settings → Secrets**:

```toml
owner_access_code = "your-long-random-owner-code"
```

The access code is read server-side and is never committed. This is a focused hackathon gate—not a production identity system. In the production design, authorization is wallet-bound and enforced by the Midnight contract owner witness; report content is encrypted to the owner’s public key.

### Demo flow

1. Open **Owner Console** as `AstraCMS Security Desk` and enter the server-configured owner access code.
2. Create two scoped local demo bounties, such as a safe attachment-preview case and an export-authorization case.
3. Open **Researcher Vault** as `nocturne_17`, select one open bounty, and submit a safe test report.
4. Use a demo collaboration key of at least eight characters. It encrypts the report before persistence.
5. Copy the salted report commitment shown in the receipt.
6. Return to **Owner Console**, select the same bounty context, and enter the collaboration key to decrypt the report locally for this browser session.
7. Accept the report. After a shielded tNIGHT transfer in Lace, paste the verified transaction/receipt commitment and mark the payout as complete.
8. Lock the owner console, then use **Command Room** to show that each bounty has its own safe public timeline.

> Never use a real target, production credential, real exploit payload, or sensitive data in the demo.

## Midnight PreProd deployment

The Compact contract lives at:

```text
midnight/contract/src/nightbounty.compact
```

The [Midnight deployment pack](midnight/README.md) explains the PreProd flow. Use the official [`example-bboard`](https://github.com/midnightntwrk/example-bboard) template as the current toolchain reference; it includes a Compact compiler-compatible setup, CLI/API patterns, Lace wallet configuration, and local Docker proof server.

After deployment, create an untracked `midnight/deployment.json` from the example file:

```bash
cp midnight/deployment.json.example midnight/deployment.json
```

Then add the **verified** PreProd contract address and deployment transaction. The Streamlit UI shows `PreProd verified` only when both are configured. It never claims local lifecycle events are public-chain transactions.

## Contract functions

```text
submitReport(commitment)
acceptReport()
rejectReport()
confirmPayout(receiptCommitment)
```

For the hackathon MVP, the Compact contract source authorizes one deployed bounty state transition and records privacy-preserving commitments. The Streamlit multi-bounty board is local demo workspace data until each bounty receives its own verified contract deployment or a future multi-bounty Compact contract is implemented. The actual reward is sent as a shielded tNIGHT transfer through Lace, then the owner commits a payout receipt. Native contract escrow is a future enhancement after validating the current Compact token-transfer primitive.

## Project structure

```text
app.py                         # Polished Streamlit UI
nightbounty/crypto.py          # Encryption and salted commitments
nightbounty/store.py           # SQLite lifecycle and public-safe events
nightbounty/midnight.py        # Honest PreProd deployment boundary
midnight/contract/             # Compact contract source
midnight/deployment.json.example
```

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall app.py nightbounty
```

## Built for the Midnight track

- Full-stack Streamlit application
- Encrypted report workflow and local persistence
- Midnight Compact contract pack
- Clear PreProd deployment path
- Meaningful privacy model
- Working, demoable responsible-disclosure lifecycle
- Setup instructions and tests
