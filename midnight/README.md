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

1. Use the current official [`example-bboard`](https://github.com/midnightntwrk/example-bboard) template as the toolchain reference. It includes the supported Compact compiler, CLI/API patterns, PreProd configuration, Lace wallet setup, and local Docker proof server.
2. Replace the example contract source with `contract/src/nightbounty.compact`.
3. Configure Lace for **Midnight PreProd**, get `tNIGHT` from the faucet, and generate `tDUST` for transaction fees.
4. Start the local proof server from the official template.
5. Install the official Compact compiler, then open a new terminal so `~/.local/bin` is on `PATH`:

   ```bash
   curl --proto '=https' --tlsv1.2 -LsSf https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
   compact --version
   ```

6. Compile the contract:

   ```bash
   cd midnight/contract
   npm install
   npm run compact
   ```

7. Deploy with the official template's PreProd CLI flow and copy the verified contract address and deployment transaction into `midnight/deployment.json`:

   ```bash
   cp midnight/deployment.json.example midnight/deployment.json
   ```

`deployment.json` is intentionally gitignored. The Streamlit UI reads it and only displays a **PreProd verified** badge when both fields are present.

## Payment scope

The hackathon MVP uses a verified contract state transition followed by a **shielded tNIGHT transfer through Lace**, then records a payout receipt commitment with `confirmPayout`.

This is intentionally safer than claiming native contract escrow without validating the current Compact token-transfer primitive. Native escrow is a post-hackathon enhancement.
