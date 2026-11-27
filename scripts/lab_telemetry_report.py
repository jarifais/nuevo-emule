#!/usr/bin/env python3
"""Validate eMule phase-1 snapshot JSONL and summarize per-session deltas.

Not an A/B analyzer: these snapshots do NOT include feature-flag acknowledgements
or source-search event latency. Never infer a performance improvement from them.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

CUMULATIVE = (
    "session_received_bytes",
    "kad_down_overhead_bytes_cumulative",
    "kad_up_overhead_bytes_cumulative",
    "server_down_overhead_bytes_cumulative",
)
KAD_CUMULATIVE = (
    "kad_slots_consumed_cumulative",
    "kad_slots_wasted_active_search_cumulative",
    "kad_lookups_started_cumulative",
    "kad_lookups_prepare_failed_cumulative",
    "kad_source_candidates_cumulative",
    "kad_new_sources_accepted_cumulative",
)
INSTANT = (
    "download_rate_bytes_per_second",
    "files_total", "files_active", "files_downloading",
    "sources_listed_total", "clients_transferring_total",
)
NUMERIC = CUMULATIVE + INSTANT + (
    "tick_ms_mod_2pow32", "elapsed_since_previous_ms",
)
FORBIDDEN = frozenset((
    "ip", "ip_address", "peer_id", "peer_hash", "file_hash",
    "filename", "file_name", "path", "port", "client_ip",
))


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp_utc must use UTC Z")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)


def validate(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ValueError("record must be an object")
    version = row.get("schema_version")
    if type(version) is not int or version not in (1, 2) or row.get("record_type") != "download_queue_snapshot":
        raise ValueError("unsupported telemetry schema or record")
    if row.get("mode") != "telemetry_only_no_feature_flags":
        raise ValueError("unknown or unverified experiment mode")
    if FORBIDDEN & set(row):
        raise ValueError("unexpected personal/network identifier in record")
    if not isinstance(row.get("session_id"), str) or not row["session_id"]:
        raise ValueError("missing session_id")
    parse_timestamp(row.get("timestamp_utc"))
    for key in NUMERIC + (KAD_CUMULATIVE if version == 2 else ()):
        value = row.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
    if row["tick_ms_mod_2pow32"] >= 2**32:
        raise ValueError("tick counter out of range")
    if not row["files_downloading"] <= row["files_active"] <= row["files_total"]:
        raise ValueError("inconsistent file counts")
    return row


def analyze(paths: list[Path]) -> dict:
    """Never accept or discard optimizations; report measurable baseline only."""
    sessions: dict[tuple[str, int], list[dict]] = defaultdict(list)
    rejected = []
    total = 0
    for path in paths:
        with path.open(encoding="utf-8-sig") as fp:
            for line_no, line in enumerate(fp, 1):
                if not line.strip():
                    continue
                total += 1
                try:
                    row = validate(json.loads(line))
                    sessions[(row["session_id"], row["schema_version"])].append(row)
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    rejected.append({"record_number": total, "reason": str(exc)})
    results = []
    for (session, version), rows in sorted(sessions.items()):
        rows.sort(key=lambda x: x["timestamp_utc"])
        elapsed = 0.0
        counters = CUMULATIVE + (KAD_CUMULATIVE if version == 2 else ())
        deltas = dict.fromkeys(counters, 0)
        valid_intervals = 0
        gaps = 0
        for earlier, later in zip(rows, rows[1:]):
            seconds = (parse_timestamp(later["timestamp_utc"]) -
                       parse_timestamp(earlier["timestamp_utc"])).total_seconds()
            if seconds <= 0:
                rejected.append({"session": session, "reason": "repeated/out-of-order timestamp"})
                continue
            if seconds > 180:
                gaps += 1
                continue  # never count disjoint time ranges as continuous
            if any(later[k] < earlier[k] for k in counters):
                rejected.append({"session": session, "reason": "cumulative counter reset"})
                continue
            valid_intervals += 1
            elapsed += seconds
            for key in counters:
                deltas[key] += later[key] - earlier[key]
        kad = ({key: deltas[key] for key in KAD_CUMULATIVE} if version == 2 else None)
        slots = deltas.get("kad_slots_consumed_cumulative", 0)
        wasted = deltas.get("kad_slots_wasted_active_search_cumulative", 0)
        started = deltas.get("kad_lookups_started_cumulative", 0)
        failed = deltas.get("kad_lookups_prepare_failed_cumulative", 0)
        accepted = deltas.get("kad_new_sources_accepted_cumulative", 0)
        results.append({
            "session_id": session,
            "schema_version": version,
            "kad_cumulative_deltas": kad,
            "kad_slot_waste_fraction": round(wasted / slots, 5) if version == 2 and slots else None,
            "kad_accepted_new_sources_per_minute": round(60 * accepted / elapsed, 5) if version == 2 and elapsed else None,
            "kad_slot_accounting_consistent": (slots == wasted + started + failed) if version == 2 and elapsed else None,
            "valid_snapshots": len(rows),
            "valid_intervals": valid_intervals,
            "coverage_seconds": elapsed,
            "disconnected_intervals": gaps,
            "cumulative_deltas": deltas,
            "mean_received_bytes_per_second": (
                round(deltas["session_received_bytes"] / elapsed, 2)
                if elapsed else None
            ),
        })
    return {
        "schema_version": 1,
        "analysis_type": "telemetry_only_not_ab",
        "automatic_adoption": False,
        "valid_snapshots": sum(len(v) for v in sessions.values()),
        "total_records": total,
        "rejected_count": len(rejected),
        "rejected_examples": rejected[:20],
        "sessions": results,
        "warning": "Kad accepted sources are list insertions, not proven usable; no Kad source latency, application-acknowledged flags or A/B inference.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, nargs="+", help="previous/current lab-telemetry JSONL")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {result['valid_snapshots']} of {result['total_records']} snapshots; "
          f"rejected {result['rejected_count']} entries.")
    print("Telemetry summary only: no automatic performance decision.")


if __name__ == "__main__":
    main()
