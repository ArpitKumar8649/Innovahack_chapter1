#!/usr/bin/env python3
"""VeritasAI evaluation harness — the difference between demo and science.

Runs the real Research Court pipeline on a labeled claim set and measures:
- label accuracy (system verdict vs gold SUPPORTS/REFUTES/NOTENOUGHINFO)
- trap catch-rate (false claims refuted) + false-alarm rate (true claims refuted)
- Expected Calibration Error (ECE): when we say 80%, are we right ~80%?
- per-category breakdown + latency/cost

Usage:
  python3 run_eval.py                    # fast subset (CI-friendly, ~13 claims)
  python3 run_eval.py --all              # full 50-claim suite
  python3 run_eval.py --claims path.jsonl --out results.json
  python3 run_eval.py --min-accuracy 0.75 --min-catch 0.90 --max-false-alarm 0.10
                                         # exit non-zero if gates fail (CI)

FEVER-format sets (claims.jsonl with gold labels) plug straight in.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "verifact" / "backend"))

from pipeline import Run, run_pipeline  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_CLAIMS = HERE / "claims.jsonl"
DEFAULT_OUT = HERE / "results.json"

# system status → FEVER label
STATUS_TO_LABEL = {
    "ESTABLISHED": "SUPPORTS",
    "SUPPORTED": "SUPPORTS",
    "REFUTED": "REFUTES",
    "CONTESTED": "NOTENOUGHINFO",
    "UNVERIFIABLE": "NOTENOUGHINFO",
    "OUTDATED": "REFUTES",
}
LABELS = ("SUPPORTS", "REFUTES", "NOTENOUGHINFO")


def load_claims(path: Path, only_fast: bool) -> list[dict]:
    claims = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        if only_fast and not c.get("fast"):
            continue
        claims.append(c)
    return claims


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def claim_verdict(report) -> tuple[str, int]:
    """The system's verdict on the CLAIM ITSELF: the claim whose text is the
    topic (extracted verbatim as claim 1), falling back to best-overlap match,
    then majority vote."""
    claims = report.claims
    if not claims:
        return "NOTENOUGHINFO", 0
    topic_n = _norm(report.topic)
    target = next((c for c in claims if _norm(c.text) == topic_n), None)
    if target is None:
        # best word-overlap match (tolerates minor LLM rewording of the premise)
        topic_words = set(topic_n.split())
        best, best_score = None, 0
        for c in claims:
            score = len(topic_words & set(_norm(c.text).split()))
            if score > best_score:
                best, best_score = c, score
        if best is not None and best_score >= max(3, len(topic_words) // 2):
            target = best
    if target is not None:
        return STATUS_TO_LABEL.get(target.status, "NOTENOUGHINFO"), target.confidence
    # fallback: majority of claim labels
    votes = [STATUS_TO_LABEL.get(c.status, "NOTENOUGHINFO") for c in claims]
    best = max(LABELS, key=lambda l: votes.count(l))
    conf = int(sum(c.confidence for c in claims) / len(claims))
    return best, conf


def expected_calibration_error(rows: list[dict], bins: int = 10) -> float:
    """ECE: weighted mean |accuracy − confidence| across confidence bins."""
    scored = [(r["confidence"] / 100, r["correct"]) for r in rows
              if r["confidence"] is not None]
    if not scored:
        return 0.0
    ece = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        in_bin = [(c, ok) for c, ok in scored if lo <= c < hi or (b == bins - 1 and c == hi)]
        if not in_bin:
            continue
        acc = sum(ok for _, ok in in_bin) / len(in_bin)
        conf = sum(c for c, _ in in_bin) / len(in_bin)
        ece += (len(in_bin) / len(scored)) * abs(acc - conf)
    return ece


async def evaluate_one(entry: dict) -> dict:
    run = Run(f"eval-{entry['id']}", entry["claim"])
    t0 = time.time()
    await run_pipeline(run)
    elapsed = round(time.time() - t0, 1)
    if run.error or run.report is None:
        return {"id": entry["id"], "claim": entry["claim"], "gold": entry["gold"],
                "category": entry.get("category", ""), "predicted": None,
                "confidence": None, "correct": False, "error": run.error,
                "elapsed_s": elapsed}
    predicted, confidence = claim_verdict(run.report)
    return {"id": entry["id"], "claim": entry["claim"], "gold": entry["gold"],
            "category": entry.get("category", ""), "predicted": predicted,
            "confidence": confidence, "correct": predicted == entry["gold"],
            "trust_score": run.report.trust_score, "error": None,
            "elapsed_s": elapsed}


async def run_suite(claims: list[dict], concurrency: int = 2) -> list[dict]:
    """Run claims with bounded concurrency (API rate limits)."""
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def guarded(entry):
        async with sem:
            r = await evaluate_one(entry)
            mark = "✓" if r["correct"] else "✗"
            print(f"  {mark} {r['id']:<22} gold={r['gold']:<14} pred={r['predicted'] or 'ERROR':<14} "
                  f"conf={r['confidence']} ({r['elapsed_s']}s)", flush=True)
            return r

    results = await asyncio.gather(*(guarded(c) for c in claims))
    return list(results)


def summarize(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["predicted"]]
    correct = sum(1 for r in valid if r["correct"])
    traps = [r for r in valid if r["category"] == "trap"]
    trues = [r for r in valid if r["category"] == "true"]
    caught = sum(1 for r in traps if r["predicted"] == "REFUTES")
    false_alarms = sum(1 for r in trues if r["predicted"] == "REFUTES")
    by_cat = {}
    for r in valid:
        cat = r["category"] or "other"
        by_cat.setdefault(cat, {"n": 0, "correct": 0})
        by_cat[cat]["n"] += 1
        by_cat[cat]["correct"] += int(r["correct"])
    # confusion matrix over the three FEVER labels
    confusion = {g: {p: 0 for p in LABELS} for g in LABELS}
    for r in valid:
        if r["gold"] in LABELS and r["predicted"] in LABELS:
            confusion[r["gold"]][r["predicted"]] += 1
    return {
        "n": len(rows), "valid": len(valid), "errors": len(rows) - len(valid),
        "error_rate": (len(rows) - len(valid)) / len(rows) if rows else 0.0,
        "accuracy": correct / len(valid) if valid else 0.0,
        "trap_catch_rate": caught / len(traps) if traps else None,
        "false_alarm_rate": false_alarms / len(trues) if trues else None,
        "ece": expected_calibration_error(valid),
        "mean_latency_s": round(sum(r["elapsed_s"] for r in rows) / len(rows), 1) if rows else 0,
        "by_category": {k: {**v, "accuracy": round(v["correct"] / v["n"], 3)}
                        for k, v in by_cat.items()},
        "confusion": confusion,
    }


def print_report(summary: dict, rows: list[dict]):
    s = summary
    print("\n" + "═" * 62)
    print("EVALUATION REPORT")
    print("═" * 62)
    print(f"  claims evaluated:   {s['valid']}/{s['n']} (error rate {s['error_rate']:.0%})")
    print(f"  label accuracy:     {s['accuracy']:.1%}")
    if s["trap_catch_rate"] is not None:
        print(f"  trap catch-rate:    {s['trap_catch_rate']:.1%}  (false claims refuted)")
    if s["false_alarm_rate"] is not None:
        print(f"  false-alarm rate:   {s['false_alarm_rate']:.1%}  (true claims wrongly refuted)")
    print(f"  ECE:                {s['ece']:.3f}  (lower = better calibrated)")
    print(f"  mean latency:       {s['mean_latency_s']}s per claim")
    print("  by category:")
    for cat, v in s["by_category"].items():
        print(f"    {cat:<12} {v['accuracy']:.1%}  ({v['correct']}/{v['n']})")
    print("  confusion (rows=gold, cols=predicted):")
    print(f"    {'':14}" + "".join(f"{l:>15}" for l in LABELS))
    for g in LABELS:
        print(f"    {g:<14}" + "".join(f"{s['confusion'][g][p]:>15}" for p in LABELS))
    wrong = [r for r in rows if r["predicted"] and not r["correct"]]
    if wrong:
        print("  misclassifications:")
        for r in wrong:
            print(f"    ✗ {r['id']}: gold={r['gold']} pred={r['predicted']} (conf {r['confidence']})")
    print("═" * 62)


def main():
    ap = argparse.ArgumentParser(description="VeritasAI evaluation harness")
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all", action="store_true", help="run the full suite (default: fast subset)")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--min-accuracy", type=float, default=None)
    ap.add_argument("--min-catch", type=float, default=None)
    ap.add_argument("--max-false-alarm", type=float, default=None)
    ap.add_argument("--max-ece", type=float, default=None)
    ap.add_argument("--max-error-rate", type=float, default=0.10)
    args = ap.parse_args()

    claims = load_claims(args.claims, only_fast=not args.all)
    print(f"Evaluating {len(claims)} claims (concurrency={args.concurrency})…\n")
    rows = asyncio.run(run_suite(claims, args.concurrency))
    summary = summarize(rows)
    print_report(summary, rows)

    args.out.write_text(json.dumps(
        {"summary": summary, "results": rows}, indent=2))
    print(f"\nResults written to {args.out}")

    # CI gates
    failures = []
    if args.max_error_rate is not None and summary["error_rate"] > args.max_error_rate:
        failures.append(f"error rate {summary['error_rate']:.0%} > {args.max_error_rate:.0%} (infra unstable — results not trustworthy)")
    if args.min_accuracy is not None and summary["accuracy"] < args.min_accuracy:
        failures.append(f"accuracy {summary['accuracy']:.1%} < {args.min_accuracy:.0%}")
    if args.min_catch is not None and (summary["trap_catch_rate"] or 0) < args.min_catch:
        failures.append(f"trap catch-rate {summary['trap_catch_rate']:.1%} < {args.min_catch:.0%}")
    if args.max_false_alarm is not None and (summary["false_alarm_rate"] or 1) > args.max_false_alarm:
        failures.append(f"false-alarm rate {summary['false_alarm_rate']:.1%} > {args.max_false_alarm:.0%}")
    if args.max_ece is not None and summary["ece"] > args.max_ece:
        failures.append(f"ECE {summary['ece']:.3f} > {args.max_ece}")
    if failures:
        print("\n❌ GATES FAILED: " + "; ".join(failures))
        sys.exit(1)
    print("\n✅ all gates passed")


if __name__ == "__main__":
    main()
