import { randomBytes } from 'node:crypto';
import type { WitnessContext } from '@midnight-ntwrk/midnight-js-protocol/compact-runtime';
import type { Ledger, Witnesses } from '../../contract/managed/nightbounty/contract/index.js';

export const nightBountyPrivateStateId = 'nightBountyPrivateState' as const;
export type NightBountyPrivateStateId = typeof nightBountyPrivateStateId;

export type NightBountyPrivateState = {
  readonly localSecretKey: Uint8Array;
};

export const createNightBountyPrivateState = (): NightBountyPrivateState => ({
  localSecretKey: new Uint8Array(randomBytes(32)),
});

export const witnesses: Witnesses<NightBountyPrivateState> = {
  localSecretKey: ({
    privateState,
  }: WitnessContext<Ledger, NightBountyPrivateState>): [NightBountyPrivateState, Uint8Array] => [
    privateState,
    privateState.localSecretKey,
  ],
};
