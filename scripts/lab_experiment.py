#!/usr/bin/env python3
"""Offline experiment plan and analysis for eMule laboratory.

This script never launches eMule or switches live features.  A Windows
integration layer must acknowledge each applied profile before data can be
accepted; that layer is not part of this script.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random
import statistics

ARMS = ("baseline", "kad_01", "ed2k_01", "udp_01", "tcp_01")
FLAGS = ARMS[1:]
SAMPLE_INTERVAL_SECONDS = 60
BLOCK_SECONDS = 6 * 3600
WARMUP_SECONDS = 30 * 60
REQUIRED_COVERAGE = 0.80
METRICS = (
    "download_bytes", "kad_useful_sources", "kad_searches_started",
    "kad_wasted_slots", "kad_udp_bytes", "ed2k_source_requests",
    "udp_retries", "tcp_connect_attempts", "tcp_connect_successes",
)


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(text: str) -> datetime:
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include UTC offset")
    return dt.astimezone(timezone.utc)


def build_plan(start: datetime, seed: int = 20261126) -> dict:
    if start.tzinfo is None:
        raise ValueError("--start requires explicit timezone offset")
    # Six days / 24 six-hour blocks, with a reference in every second block.
    # Alternating the first baseline slot per day covers every time-of-day slot.
    slots = []
    for d in range(6):
        for s in range(4):
            is_baseline = (s % 2 == d % 2)
            slots.append((d, s, is_baseline))
    candidate_positions = [i for i, (_, _, ref) in enumerate(slots) if not ref]
    rng = random.Random(seed)
    assignments = None
    best_score = None
    for _ in range(1500):
        proposals = list(FLAGS) * 3
        rng.shuffle(proposals)
        by_slot = defaultdict(list)
        by_day = defaultdict(list)
        for i, arm in zip(candidate_positions, proposals):
            d, s, _ = slots[i]
            by_slot[arm].append(s)
            by_day[d].append(arm)
        # Prefer distinct time slots and no duplicate candidate within a day.
        score = sum(max(0, len(v) - len(set(v))) * 2 for v in by_slot.values())
        score += sum(max(0, len(v) - len(set(v))) * 3 for v in by_day.values())
        if best_score is None or score < best_score:
            assignments, best_score = proposals, score
            if score == 0:
                break
    if assignments is None:
        raise RuntimeError("could not make balanced plan")
    blocks = []
    assigned = iter(assignments)
    for i, (day, slot, is_baseline) in enumerate(slots):
        arm = "baseline" if is_baseline else next(assigned)
        begin = start.astimezone(timezone.utc) + timedelta(seconds=i * BLOCK_SECONDS)
        blocks.append({
            "block_id": f"b{i+1:02d}", "day_index": day,
            "time_slot": slot, "arm": arm,
            "flags": {f: int(f == arm) for f in FLAGS},
            "start_utc": utc_iso(begin),
            "warmup_end_utc": utc_iso(begin + timedelta(seconds=WARMUP_SECONDS)),
            "end_utc": utc_iso(begin + timedelta(seconds=BLOCK_SECONDS)),
        })
    return {
        "schema_version": 1,
        "experiment_id": "lab-" + start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-s{seed}",
        "mode": "sequential_one_process",
        "experiment_days": 6,
        "block_seconds": BLOCK_SECONDS,
        "warmup_seconds": WARMUP_SECONDS,
        "sample_interval_seconds": SAMPLE_INTERVAL_SECONDS,
        "minimum_coverage": REQUIRED_COVERAGE,
        "seed": seed,
        "requires_application_acknowledgement": True,
        "acceptance_is_manual": True,
        "blocks": blocks,
    }


def validate_plan(plan: dict) -> None:
    blocks = plan["blocks"]
    if len(blocks) != 24:
        raise ValueError("expected 24 blocks")
    counts = {arm: sum(b["arm"] == arm for b in blocks) for arm in ARMS}
    if counts != {"baseline": 12, **{f: 3 for f in FLAGS}}:
        raise ValueError(f"unbalanced arms: {counts}")
    for i, b in enumerate(blocks):
        if b["flags"] != {f: int(f == b["arm"]) for f in FLAGS}:
            raise ValueError(f"wrong flags for {b['block_id']}")
        a, warm, z = map(parse_utc, (b["start_utc"], b["warmup_end_utc"], b["end_utc"]))
        if (warm-a).total_seconds() != WARMUP_SECONDS or (z-a).total_seconds() != BLOCK_SECONDS:
            raise ValueError("invalid time bounds")
        if i and a != parse_utc(blocks[i-1]["end_utc"]):
            raise ValueError("blocks are not contiguous")


def _number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be nonnegative and finite")
    return number


def analyze(plan: dict, samples: list[dict]) -> dict:
    """Analyze 1-minute samples. No automatic acceptance/rejection of features."""
    validate_plan(plan)
    blocks = {b["block_id"]: b for b in plan["blocks"]}
    by_block = defaultdict(list)
    errors = []
    seen = set()
    build_ids = {s.get("build_id") for s in samples if isinstance(s.get("build_id"), str) and s.get("build_id") }
    if len(build_ids) > 1:
        raise ValueError("multiple executable builds detected: do not pool data from different builds")
    for idx, sample in enumerate(samples, 1):
        try:
            if sample["experiment_id"] != plan["experiment_id"]:
                raise ValueError("sample does not belong to this experiment")
            if not isinstance(sample["build_id"], str) or not sample["build_id"].strip():
                raise ValueError("missing executable build identifier")
            b = blocks[sample["block_id"]]
            t = parse_utc(sample["timestamp_utc"])
            if not (parse_utc(b["start_utc"]) <= t < parse_utc(b["end_utc"])):
                raise ValueError("timestamp not in scheduled block")
            if sample["applied_flags"] != b["flags"]:
                raise ValueError("application-reported flags differ from plan")
            if not sample.get("profile_acknowledged", False):
                raise ValueError("profile was not acknowledged by application")
            if not sample.get("telemetry_healthy", False):
                raise ValueError("telemetry was not healthy")
            if (b["block_id"], t) in seen:
                raise ValueError("duplicate timestamp for block")
            seen.add((b["block_id"], t))
            values = {key: _number(sample[key], key) for key in METRICS}
            if t < parse_utc(b["warmup_end_utc"]):
                continue  # warmup is logged, never analyzed
            by_block[b["block_id"]].append(values)
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(f"sample {idx}: {exc}")
    summary = []
    required = math.ceil(((BLOCK_SECONDS-WARMUP_SECONDS)/SAMPLE_INTERVAL_SECONDS) * REQUIRED_COVERAGE)
    for b in plan["blocks"]:
        data = by_block[b["block_id"]]
        sample_count = len(data)
        row = {
            "block_id": b["block_id"], "arm": b["arm"],
            "time_slot": b["time_slot"], "valid_samples": sample_count,
            "coverage": round(sample_count / ((BLOCK_SECONDS-WARMUP_SECONDS)/SAMPLE_INTERVAL_SECONDS), 4),
            "complete": sample_count >= required,
        }
        for key in METRICS:
            row[key + "_per_minute"] = (sum(x[key] for x in data)/sample_count) if sample_count else None
        summary.append(row)
    eligible = [row for row in summary if row["complete"]]
    baseline_by_slot = defaultdict(list)
    for row in eligible:
        if row["arm"] == "baseline":
            baseline_by_slot[row["time_slot"]].append(row)
    comparisons = {}
    for arm in FLAGS:
        candidates = [r for r in eligible if r["arm"] == arm]
        matched = [r for r in candidates if len(baseline_by_slot[r["time_slot"]]) >= 1]
        metric_effects = {}
        for m in METRICS:
            key = m + "_per_minute"
            differences = []
            for r in matched:
                reference = statistics.mean(x[key] for x in baseline_by_slot[r["time_slot"]])
                if reference > 0:
                    differences.append((r[key] / reference - 1) * 100)
            metric_effects[m + "_relative_percent"] = (round(statistics.mean(differences), 3)
                if len(differences) == len(matched) and differences else None)
        comparisons[arm] = {
            "candidate_blocks_complete": len(candidates),
            "matched_blocks": len(matched),
            "decision": "inconclusive_no_automatic_adoption",
            "evidence_grade": ("preliminary" if len(matched) >= 3 else "insufficient"),
            "note": "Nonstationary peer availability, changing files, and time trends may bias comparison; no causal claim.",
            "relative_effects": metric_effects,
        }
    return {
        "schema_version": 1,
        "automatic_decision": False,
        "experiment_id": plan["experiment_id"],
        "build_id": (next(iter(build_ids)) if build_ids else None),
        "total_samples_received": len(samples),
        "invalid_sample_count": len(errors),
        "invalid_sample_examples": errors[:20],
        "valid_blocks": len(eligible),
        "required_samples_per_block": required,
        "blocks": summary,
        "comparisons": comparisons,
    }


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise ValueError(f"JSONL line {line_no} is not an object")
                records.append(obj)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan", help="write reproducible 6-day schedule")
    plan_parser.add_argument("--start", required=True, help="ISO-8601 timestamp with UTC offset")
    plan_parser.add_argument("--seed", type=int, default=20261126)
    plan_parser.add_argument("--out", type=Path, required=True)
    report_parser = commands.add_parser("report", help="analyze recorded 1-minute app telemetry")
    report_parser.add_argument("--plan", type=Path, required=True)
    report_parser.add_argument("--samples", type=Path, required=True)
    report_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        plan = build_plan(datetime.fromisoformat(args.start), args.seed)
        validate_plan(plan)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        report = analyze(plan, load_jsonl(args.samples))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"valid blocks: {report['valid_blocks']}, invalid samples: {report['invalid_sample_count']}")
        print("This tool does not approve or discard improvements automatically.")


if __name__ == "__main__":
    main()
