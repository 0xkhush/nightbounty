# Midnight PreProd pack

NightBounty uses a Compact contract to prove the bounty lifecycle without putting vulnerability details on-chain:

```text
OPEN → REPORT_SUBMITTED → ACCEPTED / REJECTED → PAID
```

## Contract scope boundary

`contract/src/nightbounty.compact` models **one bounty per deployed contract instance**. The Streamlit app can create multiple local demo bounties for a single owner so judges can see the product workflow, but those locally created records are not represented as separate PreProd deployments.

To support several on-chain bounties, deploy one contract instance per bounty or implement and validate a future keyed multi-bounty Compact design. Do not claim the local workspace actions are chain transactions until the application invokes verified deployed bindings.

## What is private

- Raw vulnerability report and proof-of-concept
- Researcher pseudonym
- Shielded payout recipient
- Payout receipt details

## What is verifiable

- The contract deployment
- The current bounty state
- A report commitment was submitted first
- The owner accepted/rejected it
- A payout receipt commitment was recorded

## Deploy during the hackathon

1. Use the included [`deployer/`](deployer/README.md) package. It is a NightBounty-specific adaptation of the official [`example-bboard`](https://github.com/midnightntwrk/example-bboard) provider patterns; do not deploy the bulletin-board example contract.
2. Compile `contract/src/nightbounty.compact` with the matching Compact language compiler so `contract/managed/nightbounty` exists.
3. From `midnight/deployer`, run `npm ci`, `npm run proof-server:up`, and `npm run deploy`. The runner creates or recovers a local PreProd wallet, requests tNIGHT, generates tDUST, and deploys NightBounty.
4. Save the recovery seed and encrypted `.private-state/` password offline. They are required for later owner-only contract calls.
5. If the faucet does not respond automatically, use the public address printed by the runner at the PreProd faucet, then rerun with the same recovery seed.
6. If you need to compile manually, install the official Compact compiler, then open a new terminal so `~/.local/bin` is on `PATH`:

   ```bash
   curl --proto '=https' --tlsv1.2 -LsSf https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
   compact --version
   ```

7. Copy the deployer’s verified `contractAddress` and `deployTxHash` into `midnight/deployment.json`:

   ```bash
   cp midnight/deployment.json.example midnight/deployment.json
   ```

`deployment.json` is intentionally gitignored. The Streamlit UI reads it and only displays a **PreProd verified** badge when both fields are present.

## Payment scope

The hackathon MVP uses a verified contract state transition followed by a **shielded tNIGHT transfer through Lace**, then records a payout receipt commitment with `confirmPayout`.

This is intentionally safer than claiming native contract escrow without validating the current Compact token-transfer primitive. Native escrow is a post-hackathon enhancement.
