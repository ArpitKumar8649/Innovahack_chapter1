#!/usr/bin/env python3
"""Load a FEVER-format dataset into the harness's claims.jsonl format.

FEVER (Thorne et al.): 185k claims labeled SUPPORTS / REFUTES / NOTENOUGHINFO
with gold evidence sentences. Standard benchmark for claim verification.

Download the paper-dev set, then:
  python3 load_fever.py --in fever-dev.jsonl --out fever_claims.jsonl --n 200

Each FEVER line: {"id": ..., "claim": "...", "label": "SUPPORTS|REFUTES|NOTENOUGHINFO", ...}
Output lines match claims.jsonl so run_eval.py consumes them unchanged:
  python3 run_eval.py --claims fever_claims.jsonl --all
"""
import argparse
import json
import random
from pathlib import Path

LABELS = {"SUPPORTS", "REFUTES", "NOTENOUGHINFO"}


def main():
    ap = argparse.ArgumentParser(description="Convert a FEVER jsonl to claims.jsonl")
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=200, help="claims per label (stratified)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    by_label = {l: [] for l in LABELS}
    for line in args.src.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        label = row.get("label")
        claim = (row.get("claim") or "").strip()
        if label in LABELS and claim:
            by_label[label].append({"id": f"fever_{row.get('id')}", "claim": claim,
                                    "gold": label, "category": "fever"})

    random.seed(args.seed)
    out = []
    for label, rows in by_label.items():
        random.shuffle(rows)
        out.extend(rows[:args.n])
    random.shuffle(out)

    args.out.write_text("\n".join(json.dumps(r) for r in out) + "\n")
    counts = {l: min(len(rows), args.n) for l, rows in by_label.items()}
    print(f"Wrote {len(out)} claims to {args.out} — {counts}")


if __name__ == "__main__":
    main()
