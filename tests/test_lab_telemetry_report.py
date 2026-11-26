import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lab_telemetry_report import analyze, validate


def row(at, received, session="test-session", **extra):
    result = {
        "schema_version": 1,
        "record_type": "download_queue_snapshot",
        "mode": "telemetry_only_no_feature_flags",
        "session_id": session,
        "timestamp_utc": at,
        "tick_ms_mod_2pow32": 100000,
        "elapsed_since_previous_ms": 60000,
        "download_rate_bytes_per_second": 80,
        "files_total": 4,
        "files_active": 3,
        "files_downloading": 2,
        "sources_listed_total": 15,
        "clients_transferring_total": 2,
        "session_received_bytes": received,
        "kad_down_overhead_bytes_cumulative": received // 100,
        "kad_up_overhead_bytes_cumulative": received // 200,
        "server_down_overhead_bytes_cumulative": received // 50,
    }
    result.update(extra)
    return result


class TestLabTelemetry(unittest.TestCase):
    def test_field_validation(self):
        self.assertEqual(validate(row("2026-11-26T12:00:00Z", 1000))["files_total"], 4)

    def test_reject_identifiers(self):
        with self.assertRaises(ValueError):
            validate(row("2026-11-26T12:00:00Z", 1000, ip="127.0.0.1"))

    def test_reject_missing_and_invalid_counters(self):
        with self.assertRaises(ValueError):
            validate(row("2026-11-26T12:00:00Z", 1000, files_total=-1))
        with self.assertRaises(ValueError):
            validate(row("2026-11-26T12:00:00Z", 1000, files_total=None))

    def test_monotonic_delta_and_no_ab_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.jsonl"
            values = [
                row("2026-11-26T12:00:00Z", 1000),
                row("2026-11-26T12:01:00Z", 7000),
                row("2026-11-26T12:02:00Z", 8000),
            ]
            path.write_text("\n".join(json.dumps(v) for v in values) + "\n", encoding="utf-8")
            report = analyze([path])
            self.assertFalse(report["automatic_adoption"])
            self.assertEqual(report["analysis_type"], "telemetry_only_not_ab")
            self.assertEqual(report["sessions"][0]["cumulative_deltas"]["session_received_bytes"], 7000)
            self.assertEqual(report["sessions"][0]["coverage_seconds"], 120)

    def test_no_data_no_conclusion(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            report = analyze([path])
            self.assertEqual(report["sessions"], [])
            self.assertFalse(report["automatic_adoption"])

    def test_gap_and_counter_reset_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.jsonl"
            values = [
                row("2026-11-26T12:00:00Z", 1000),
                row("2026-11-26T12:01:00Z", 2000),
                row("2026-11-26T12:02:00Z", 100),
                row("2026-11-26T12:10:00Z", 300),
            ]
            path.write_text("\n".join(json.dumps(v) for v in values) + "\n", encoding="utf-8")
            report = analyze([path])
            self.assertEqual(report["sessions"][0]["valid_intervals"], 1)
            self.assertEqual(report["sessions"][0]["disconnected_intervals"], 1)
            self.assertGreater(report["rejected_count"], 0)


if __name__ == "__main__":
    unittest.main()
