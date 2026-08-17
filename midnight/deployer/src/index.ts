import { mkdir } from 'node:fs/promises';
import { stderr, stdout } from 'node:process';
import { Contract } from '../../contract/managed/nightbounty/contract/index.js';
import { CompiledContract } from '@midnight-ntwrk/midnight-js-protocol/compact-js';
import { deployContract } from '@midnight-ntwrk/midnight-js-contracts';
import { httpClientProofProvider } from '@midnight-ntwrk/midnight-js-http-client-proof-provider';
import { indexerPublicDataProvider } from '@midnight-ntwrk/midnight-js-indexer-public-data-provider';
import { levelPrivateStateProvider } from '@midnight-ntwrk/midnight-js-level-private-state-provider';
import { setNetworkId } from '@midnight-ntwrk/midnight-js-network-id';
import { NodeZkConfigProvider } from '@midnight-ntwrk/midnight-js-node-zk-config-provider';
import { unshieldedToken } from '@midnight-ntwrk/midnight-js-protocol/ledger';
import type { MidnightProviders } from '@midnight-ntwrk/midnight-js-types';
import { WebSocket } from 'ws';
import {
  NIGHT_BOUNTY_ARTIFACT_DIRECTORY,
  PREPROD_ENVIRONMENT,
  PRIVATE_STATE_DIRECTORY,
  PRIVATE_STATE_STORE,
  SIGNING_KEY_STORE,
} from './config.js';
import {
  createNightBountyPrivateState,
  nightBountyPrivateStateId,
  type NightBountyPrivateState,
  type NightBountyPrivateStateId,
  witnesses,
} from './private-state.js';
import {
  promptStoragePassword,
  promptWalletIntent,
  revealAndConfirmFreshSeed,
  status,
} from './prompt.js';
import { ensureTDust, waitForUnshieldedFunds } from './wallet-flow.js';
import { MidnightWalletProvider } from './wallet.js';

// Apollo's Node transport needs a WebSocket implementation for indexer subscriptions.
// @ts-expect-error ws supplies the browser-compatible constructor expected by Apollo.
globalThis.WebSocket = WebSocket;

type NightBountyContract = Contract<NightBountyPrivateState, typeof witnesses>;
type NightBountyCircuitKey = Exclude<keyof NightBountyContract['impureCircuits'], number | symbol>;
type NightBountyProviders = MidnightProviders<
  NightBountyCircuitKey,
  NightBountyPrivateStateId,
  NightBountyPrivateState
>;

const compiledNightBountyContract = CompiledContract.make<NightBountyContract>(
  'NightBounty',
  Contract,
).pipe(
  CompiledContract.withWitnesses(witnesses),
  CompiledContract.withCompiledFileAssets(NIGHT_BOUNTY_ARTIFACT_DIRECTORY),
);

type PublicDeploymentEvidence = {
  readonly network: 'preprod';
  readonly contractAddress: string;
  readonly deployTxHash: string;
  readonly blockHeight: string;
  readonly compactCompiler: '0.31.1';
  readonly compactRuntime: '0.16.0';
};

const publicValue = (value: unknown): string => {
  if (value instanceof Uint8Array) {
    return Buffer.from(value).toString('hex');
  }
  if (typeof value === 'object' && value !== null && 'bytes' in value) {
    const bytes = (value as { bytes: unknown }).bytes;
    if (bytes instanceof Uint8Array) {
      return Buffer.from(bytes).toString('hex');
    }
  }
  return String(value);
};

const run = async (): Promise<void> => {
  setNetworkId('preprod');
  const intent = await promptWalletIntent();
  const builtWallet = await MidnightWalletProvider.build(
    PREPROD_ENVIRONMENT,
    intent.kind === 'recover' ? intent.seed : undefined,
  );

  if (intent.kind === 'new') {
    await revealAndConfirmFreshSeed(builtWallet.masterSeed);
  }

  const privateStoragePassword = await promptStoragePassword();
  await mkdir(PRIVATE_STATE_DIRECTORY, { recursive: true });

  try {
    await builtWallet.provider.start();
    const unshieldedState = await waitForUnshieldedFunds(
      builtWallet.provider.wallet,
      PREPROD_ENVIRONMENT,
      unshieldedToken(),
    );
    await ensureTDust(builtWallet.masterSeed, unshieldedState, builtWallet.provider.wallet);

    const zkConfigProvider = new NodeZkConfigProvider<NightBountyCircuitKey>(NIGHT_BOUNTY_ARTIFACT_DIRECTORY);
    const privateStateProvider = levelPrivateStateProvider<NightBountyPrivateStateId, NightBountyPrivateState>({
      privateStateStoreName: PRIVATE_STATE_STORE,
      signingKeyStoreName: SIGNING_KEY_STORE,
      privateStoragePasswordProvider: () => privateStoragePassword,
      accountId: builtWallet.masterSeed,
    });
    const providers: NightBountyProviders = {
      privateStateProvider,
      publicDataProvider: indexerPublicDataProvider(PREPROD_ENVIRONMENT.indexer, PREPROD_ENVIRONMENT.indexerWS),
      zkConfigProvider,
      proofProvider: httpClientProofProvider(PREPROD_ENVIRONMENT.proofServer, zkConfigProvider),
      walletProvider: builtWallet.provider,
      midnightProvider: builtWallet.provider,
    };

    status('Submitting the NightBounty deployment transaction to Midnight PreProd…');
    const deployedContract = await deployContract(providers, {
      compiledContract: compiledNightBountyContract,
      privateStateId: nightBountyPrivateStateId,
      initialPrivateState: createNightBountyPrivateState(),
    });
    privateStateProvider.setContractAddress(deployedContract.deployTxData.public.contractAddress);

    const evidence: PublicDeploymentEvidence = {
      network: 'preprod',
      contractAddress: publicValue(deployedContract.deployTxData.public.contractAddress),
      deployTxHash: publicValue(deployedContract.deployTxData.public.txHash),
      blockHeight: publicValue(deployedContract.deployTxData.public.blockHeight),
      compactCompiler: '0.31.1',
      compactRuntime: '0.16.0',
    };
    stdout.write(`${JSON.stringify(evidence)}\n`);
  } finally {
    await builtWallet.provider.stop().catch(() => undefined);
  }
};

try {
  await run();
} catch {
  stderr.write('Deployment failed; no public deployment evidence was emitted.\n');
  process.exitCode = 1;
}
