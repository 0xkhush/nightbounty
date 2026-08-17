import {
  type CoinPublicKey,
  DustSecretKey,
  type EncPublicKey,
  type FinalizedTransaction,
  LedgerParameters,
  ZswapSecretKeys,
} from '@midnight-ntwrk/midnight-js-protocol/ledger';
import type { MidnightProvider, UnboundTransaction, WalletProvider } from '@midnight-ntwrk/midnight-js-types';
import { ttlOneHour } from '@midnight-ntwrk/midnight-js-utils';
import type { WalletFacade } from '@midnight-ntwrk/wallet-sdk-facade';
import { type DustWalletOptions, type EnvironmentConfiguration, FluentWalletBuilder } from '@midnight-ntwrk/testkit-js';

type UnshieldedKeystore = {
  getPublicKey(): unknown;
  signData(payload: Uint8Array): string;
};

type WalletBuildResult = {
  wallet: WalletFacade;
  seeds: {
    masterSeed: string;
    shielded: Uint8Array;
    dust: Uint8Array;
  };
  keystore: UnshieldedKeystore;
};

export type BuiltWallet = {
  readonly provider: MidnightWalletProvider;
  readonly masterSeed: string;
};

export class MidnightWalletProvider implements MidnightProvider, WalletProvider {
  private constructor(
    readonly wallet: WalletFacade,
    readonly unshieldedKeystore: UnshieldedKeystore,
    readonly zswapSecretKeys: ZswapSecretKeys,
    readonly dustSecretKey: DustSecretKey,
  ) {}

  getCoinPublicKey(): CoinPublicKey {
    return this.zswapSecretKeys.coinPublicKey;
  }

  getEncryptionPublicKey(): EncPublicKey {
    return this.zswapSecretKeys.encryptionPublicKey;
  }

  async balanceTx(tx: UnboundTransaction, ttl: Date = ttlOneHour()): Promise<FinalizedTransaction> {
    const recipe = await this.wallet.balanceUnboundTransaction(
      tx,
      { shieldedSecretKeys: this.zswapSecretKeys, dustSecretKey: this.dustSecretKey },
      { ttl },
    );
    const signedRecipe = await this.wallet.signRecipe(recipe, (payload) => this.unshieldedKeystore.signData(payload));
    return this.wallet.finalizeRecipe(signedRecipe);
  }

  submitTx(tx: FinalizedTransaction): Promise<string> {
    return this.wallet.submitTransaction(tx);
  }

  start(): Promise<void> {
    return this.wallet.start(this.zswapSecretKeys, this.dustSecretKey);
  }

  stop(): Promise<void> {
    return this.wallet.stop();
  }

  static async build(environment: EnvironmentConfiguration, recoverySeed?: string): Promise<BuiltWallet> {
    const dustOptions: DustWalletOptions = {
      ledgerParams: LedgerParameters.initialParameters(),
      additionalFeeOverhead: environment.walletNetworkId === 'undeployed' ? 500_000_000_000_000_000n : 1_000n,
      feeBlocksMargin: 5,
    };
    const builder = FluentWalletBuilder.forEnvironment(environment).withDustOptions(dustOptions);
    const result = (recoverySeed
      ? await builder.withSeed(recoverySeed).buildWithoutStarting()
      : await builder.withRandomSeed().buildWithoutStarting()) as unknown as WalletBuildResult;

    return {
      provider: new MidnightWalletProvider(
        result.wallet,
        result.keystore,
        ZswapSecretKeys.fromSeed(result.seeds.shielded),
        DustSecretKey.fromSeed(result.seeds.dust),
      ),
      masterSeed: result.seeds.masterSeed,
    };
  }
}
