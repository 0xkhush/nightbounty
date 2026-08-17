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

The app intentionally demonstrates one fully working bounty case:

```text
OPEN → REPORT_SUBMITTED → ACCEPTED / REJECTED → PAID
```

A one-bounty Compact contract is a deliberate scope decision: it produces a real, understandable Midnight lifecycle in two hours rather than a broad marketplace with shallow or fake integration.

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

### Demo flow

1. Open **Researcher Vault**.
2. Submit a safe test report for the isolated AstraCMS training target.
3. Use a demo collaboration key of at least eight characters. It encrypts the report before persistence.
4. Copy the salted report commitment shown in the receipt.
5. Open **Owner Console** and enter the same collaboration key to decrypt the report locally for the browser session.
6. Accept the report.
7. After making a shielded tNIGHT transfer in Lace, paste the verified transaction/receipt commitment and mark the payout as complete.
8. Return to **Command Room** and show the safe public timeline.

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

For the hackathon MVP, the contract authorizes the bounty state transition and records privacy-preserving commitments. The actual reward is sent as a shielded tNIGHT transfer through Lace, then the owner commits a payout receipt. Native contract escrow is a future enhancement after validating the current Compact token-transfer primitive.

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
