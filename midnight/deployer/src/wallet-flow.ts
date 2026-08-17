import type { UnshieldedTokenType } from '@midnight-ntwrk/midnight-js-protocol/ledger';
import { getNetworkId } from '@midnight-ntwrk/midnight-js-network-id';
import type { WalletFacade, FacadeState } from '@midnight-ntwrk/wallet-sdk-facade';
import { UnshieldedAddress } from '@midnight-ntwrk/wallet-sdk-address-format';
import { createKeystore, type UnshieldedWalletState } from '@midnight-ntwrk/wallet-sdk-unshielded-wallet';
import { HDWallet, Roles } from '@midnight-ntwrk/wallet-sdk-hd';
import { FaucetClient, type EnvironmentConfiguration } from '@midnight-ntwrk/testkit-js';
import pino from 'pino';
import { filter, firstValueFrom, map, take, timeout } from 'rxjs';
import { FUNDING_TIMEOUT_MS } from './config.js';
import { status } from './prompt.js';

const silentLogger = pino({ level: 'silent' });

const isProgressStrictlyComplete = (progress: unknown): boolean => {
  if (typeof progress !== 'object' || progress === null) {
    return false;
  }
  const candidate = progress as { isStrictlyComplete?: unknown };
  return typeof candidate.isStrictlyComplete === 'function' && candidate.isStrictlyComplete();
};

const isFacadeStateSynced = (state: FacadeState): boolean =>
  isProgressStrictlyComplete(state.shielded.state.progress) &&
  isProgressStrictlyComplete(state.dust.state.progress) &&
  isProgressStrictlyComplete(state.unshielded.progress);

const waitForSyncedState = async (wallet: WalletFacade): Promise<FacadeState> =>
  firstValueFrom(
    wallet.state().pipe(
      filter(isFacadeStateSynced),
      take(1),
      timeout({ first: FUNDING_TIMEOUT_MS }),
    ),
  );

export const waitForUnshieldedFunds = async (
  wallet: WalletFacade,
  environment: EnvironmentConfiguration,
  tokenType: UnshieldedTokenType,
): Promise<UnshieldedWalletState> => {
  const initialState = await firstValueFrom(wallet.unshielded.state);
  const currentBalance = initialState.balances[tokenType.raw] ?? 0n;
  if (currentBalance > 0n) {
    return initialState;
  }

  if (!environment.faucet) {
    throw new Error('The PreProd faucet endpoint is not configured.');
  }

  const address = UnshieldedAddress.codec.encode(getNetworkId(), initialState.address).toString();
  status(`PreProd faucet address: ${address}`);
  status('Requesting PreProd faucet funding and waiting for wallet synchronization…');
  await new FaucetClient(environment.faucet, silentLogger).requestTokens(address);

  return firstValueFrom(
    wallet.state().pipe(
      filter(isFacadeStateSynced),
      filter((state) => (state.unshielded.balances[tokenType.raw] ?? 0n) > 0n),
      map((state) => state.unshielded),
      take(1),
      timeout({ first: FUNDING_TIMEOUT_MS }),
    ),
  );
};

const unshieldedSeedFromMasterSeed = (masterSeed: string): Uint8Array => {
  const result = HDWallet.fromSeed(Buffer.from(masterSeed, 'hex')) as { type: string; hdWallet?: HDWallet };
  if (result.type !== 'seedOk' || !result.hdWallet) {
    throw new Error('Unable to derive the unshielded wallet key from the recovery seed.');
  }

  const derivation = result.hdWallet.selectAccount(0).selectRole(Roles.NightExternal).deriveKeyAt(0);
  if (derivation.type === 'keyOutOfBounds') {
    throw new Error('Unshielded key derivation is out of bounds.');
  }
  return derivation.key;
};

export const ensureTDust = async (
  masterSeed: string,
  unshieldedState: UnshieldedWalletState,
  wallet: WalletFacade,
): Promise<void> => {
  const dustState = await wallet.dust.waitForSyncedState();
  if (dustState.balance(new Date()) > 0n) {
    return;
  }

  const availableUtxos = unshieldedState.availableCoins.filter((coin) => !coin.meta.registeredForDustGeneration);
  if (availableUtxos.length === 0) {
    throw new Error('No unregistered faucet UTXOs are available for tDUST generation.');
  }

  status('Registering faucet UTXOs for tDUST generation…');
  const unshieldedKeystore = createKeystore(unshieldedSeedFromMasterSeed(masterSeed), getNetworkId());
  const recipe = await wallet.registerNightUtxosForDustGeneration(
    availableUtxos,
    unshieldedKeystore.getPublicKey(),
    (payload) => unshieldedKeystore.signData(payload),
    dustState.address,
  );
  const transaction = await wallet.finalizeRecipe(recipe);
  await wallet.submitTransaction(transaction);

  status('Waiting for tDUST to become available…');
  await firstValueFrom(
    wallet.state().pipe(
      filter((state) => state.dust.balance(new Date()) > 0n),
      take(1),
      timeout({ first: FUNDING_TIMEOUT_MS }),
    ),
  );
  await waitForSyncedState(wallet);
};
