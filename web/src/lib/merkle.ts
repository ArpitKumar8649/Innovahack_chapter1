/* Client-side Merkle verification — mirrors backend/evidence.py exactly. */
import type { MerkleStep } from "../types";

export async function sha256Hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Walk a Merkle proof path from a leaf hash up to the root. */
export async function verifyMerkle(
  leafHash: string,
  proof: MerkleStep[] | undefined,
  root: string,
): Promise<boolean> {
  let cur = leafHash;
  for (const p of proof ?? []) {
    cur = p.side === "right" ? await sha256Hex(cur + p.hash) : await sha256Hex(p.hash + cur);
  }
  return cur === root;
}
