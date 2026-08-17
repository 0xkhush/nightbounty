import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { EnvironmentConfiguration } from '@midnight-ntwrk/testkit-js';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export const NIGHT_BOUNTY_ARTIFACT_DIRECTORY = resolve(packageRoot, '../contract/managed/nightbounty');
export const PRIVATE_STATE_DIRECTORY = resolve(packageRoot, '.private-state');
export const PRIVATE_STATE_STORE = resolve(PRIVATE_STATE_DIRECTORY, 'nightbounty-preprod');
export const SIGNING_KEY_STORE = resolve(PRIVATE_STATE_DIRECTORY, 'nightbounty-preprod-signing-keys');

export const PREPROD_ENVIRONMENT: EnvironmentConfiguration = {
  walletNetworkId: 'preprod',
  networkId: 'preprod',
  indexer: 'https://indexer.preprod.midnight.network/api/v4/graphql',
  indexerWS: 'wss://indexer.preprod.midnight.network/api/v4/graphql/ws',
  node: 'https://rpc.preprod.midnight.network',
  nodeWS: 'wss://rpc.preprod.midnight.network',
  faucet: 'https://midnight-tmnight-preprod.nethermind.dev/',
  proofServer: 'http://127.0.0.1:6300',
};

export const FUNDING_TIMEOUT_MS = 10 * 60 * 1_000;
