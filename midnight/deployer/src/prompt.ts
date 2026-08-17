import { createInterface } from 'node:readline/promises';
import { stdin, stderr } from 'node:process';

const requireTerminal = (): void => {
  if (!stdin.isTTY || !stderr.isTTY) {
    throw new Error('An interactive TTY is required so recovery material and the storage password are never piped.');
  }
};

const promptLine = async (label: string): Promise<string> => {
  requireTerminal();
  const readline = createInterface({ input: stdin, output: stderr, terminal: true });
  try {
    return (await readline.question(label)).trim();
  } finally {
    readline.close();
  }
};

export const promptSecret = async (label: string): Promise<string> => {
  requireTerminal();
  stderr.write(label);

  return new Promise<string>((resolve, reject) => {
    const previousRawMode = stdin.isRaw;
    let answer = '';

    const cleanUp = (): void => {
      stdin.off('data', onData);
      stdin.setRawMode(previousRawMode ?? false);
      stderr.write('\n');
    };

    const finish = (): void => {
      cleanUp();
      resolve(answer);
    };

    const abort = (): void => {
      cleanUp();
      reject(new Error('Prompt cancelled.'));
    };

    const onData = (chunk: Buffer): void => {
      for (const character of chunk.toString('utf8')) {
        if (character === '\r' || character === '\n') {
          finish();
          return;
        }
        if (character === '\u0003') {
          abort();
          return;
        }
        if (character === '\u007f' || character === '\b') {
          if (answer.length > 0) {
            answer = answer.slice(0, -1);
            stderr.write('\b \b');
          }
          continue;
        }
        if (character >= ' ') {
          answer += character;
          stderr.write('*');
        }
      }
    };

    stdin.setRawMode(true);
    stdin.resume();
    stdin.on('data', onData);
  });
};

export type WalletIntent = { readonly kind: 'new' } | { readonly kind: 'recover'; readonly seed: string };

export const promptWalletIntent = async (): Promise<WalletIntent> => {
  while (true) {
    const choice = await promptLine('Wallet: [1] create new, [2] recover from 32-byte hex seed: ');
    if (choice === '1') {
      return { kind: 'new' };
    }
    if (choice === '2') {
      const seed = (await promptSecret('Recovery seed (hidden): ')).trim();
      if (/^[0-9a-fA-F]{64}$/.test(seed)) {
        return { kind: 'recover', seed: seed.toLowerCase() };
      }
      stderr.write('A recovery seed must be exactly 64 hexadecimal characters.\n');
      continue;
    }
    stderr.write('Enter 1 or 2.\n');
  }
};

export const revealAndConfirmFreshSeed = async (seed: string): Promise<void> => {
  requireTerminal();
  stderr.write('\nSave this new wallet recovery seed in an offline password manager. It is shown once and is never written to disk:\n');
  stderr.write(`${seed}\n`);
  const confirmation = (await promptSecret('Re-enter the recovery seed to confirm it is backed up (hidden): ')).trim();
  if (confirmation !== seed) {
    throw new Error('Recovery seed confirmation did not match. No deployment was submitted.');
  }
};

export const promptStoragePassword = async (): Promise<string> => {
  while (true) {
    const password = await promptSecret('Private-state encryption password (hidden): ');
    if (password.length < 12) {
      stderr.write('Use at least 12 characters.\n');
      continue;
    }
    const confirmation = await promptSecret('Confirm private-state encryption password (hidden): ');
    if (password === confirmation) {
      return password;
    }
    stderr.write('Passwords did not match.\n');
  }
};

export const status = (message: string): void => {
  stderr.write(`${message}\n`);
};
