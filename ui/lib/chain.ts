import { blake2bHex } from "blakejs";

import { GovernanceEntry } from "./api";

/**
 * Recompute the ledger's hash chain in the browser.
 *
 * The API sends each entry's canonical payload bytes alongside the stored
 * digest, and this redoes the BLAKE2b-128 itself rather than trusting the
 * server's verdict. Two independent things are checked per entry: that the
 * digest matches the payload it claims to cover, and that the entry points at
 * the digest of the one before it. Either failing breaks the chain from there.
 */
export type CheckedEntry = GovernanceEntry & {
  recomputed: string;
  digestOk: boolean;
  linkOk: boolean;
};

export type ChainResult = {
  entries: CheckedEntry[];
  verified: boolean;
  breakAt: number | null;
};

export function digestEntry(prevHash: string, canonical: string): string {
  return blake2bHex(prevHash + canonical, undefined, 16);
}

export function verifyChain(
  entries: GovernanceEntry[],
  genesis: string,
  tamper?: { index: number; canonical: string },
): ChainResult {
  let prev = genesis;
  let breakAt: number | null = null;
  const checked: CheckedEntry[] = [];

  entries.forEach((entry, i) => {
    const canonical =
      tamper && tamper.index === i ? tamper.canonical : (entry.canonical ?? "");
    const recomputed = digestEntry(entry.prev_hash, canonical);
    const digestOk = recomputed === entry.entry_hash;
    const linkOk = entry.prev_hash === prev;
    if ((!digestOk || !linkOk) && breakAt === null) breakAt = i;
    checked.push({ ...entry, recomputed, digestOk, linkOk });
    prev = entry.entry_hash;
  });

  return { entries: checked, verified: breakAt === null, breakAt };
}

/**
 * Flip the first number in a canonical payload, to demonstrate that editing run
 * history is detectable. Returns null when there is nothing numeric to change.
 */
export function tamperedCanonical(canonical: string): string | null {
  const match = canonical.match(/:(-?\d+\.?\d*)/);
  if (!match) return null;
  const original = match[1];
  const bumped = original.includes(".")
    ? (parseFloat(original) + 0.1).toFixed(4)
    : String(parseInt(original, 10) + 1);
  return canonical.replace(`:${original}`, `:${bumped}`);
}
