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



def kad_row(at, received, session="kad-test-session", **extra):
    """V2 event counters are cumulative and remain intact if a snapshot write fails."""
    result = row(at, received, session=session)
    result["schema_version"] = 2
    result.update({name: 0 for name in (
        "kad_slots_consumed_cumulative",
        "kad_slots_wasted_active_search_cumulative",
        "kad_lookups_started_cumulative",
        "kad_lookups_prepare_failed_cumulative",
        "kad_source_candidates_cumulative",
        "kad_new_sources_accepted_cumulative",
    )})
    result.update(extra)
    return result


class TestKadTelemetryV2(unittest.TestCase):
    def test_v2_kad_counters_and_rates(self):
        from lab_telemetry_report import KAD_CUMULATIVE
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "v2.jsonl"
            records = [
                kad_row("2026-11-26T12:00:00Z", 1000),
                kad_row("2026-11-26T12:01:00Z", 2000,
                        kad_slots_consumed_cumulative=4,
                        kad_slots_wasted_active_search_cumulative=1,
                        kad_lookups_started_cumulative=2,
                        kad_lookups_prepare_failed_cumulative=1,
                        kad_source_candidates_cumulative=5,
                        kad_new_sources_accepted_cumulative=3),
                kad_row("2026-11-26T12:02:00Z", 5000,
                        kad_slots_consumed_cumulative=8,
                        kad_slots_wasted_active_search_cumulative=2,
                        kad_lookups_started_cumulative=5,
                        kad_lookups_prepare_failed_cumulative=1,
                        kad_source_candidates_cumulative=7,
                        kad_new_sources_accepted_cumulative=4),
            ]
            path.write_text("\n".join(map(json.dumps, records)) + "\n", encoding="utf-8")
            report = analyze([path])
            self.assertEqual(report["rejected_count"], 0)
            self.assertEqual(report["analysis_type"], "telemetry_only_not_ab")
            session = report["sessions"][0]
            self.assertEqual(set(session["kad_cumulative_deltas"]), set(KAD_CUMULATIVE))
            self.assertEqual(session["kad_cumulative_deltas"]["kad_slots_consumed_cumulative"], 8)
            self.assertEqual(session["kad_cumulative_deltas"]["kad_new_sources_accepted_cumulative"], 4)
            self.assertTrue(session["kad_slot_accounting_consistent"])
            self.assertEqual(session["kad_slot_waste_fraction"], 0.25)
            self.assertEqual(session["kad_accepted_new_sources_per_minute"], 2.0)

    def test_v2_rejects_missing_counter(self):
        record = kad_row("2026-11-26T12:00:00Z", 0)
        del record["kad_lookups_started_cumulative"]
        with self.assertRaises(ValueError):
            validate(record)

    def test_legacy_and_v2_never_merge_into_one_session(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "mixed.jsonl"
            records = [
                row("2026-11-26T12:00:00Z", 0, session="same-id"),
                row("2026-11-26T12:01:00Z", 1000, session="same-id"),
                kad_row("2026-11-26T12:02:00Z", 2000, session="same-id"),
                kad_row("2026-11-26T12:03:00Z", 3000, session="same-id"),
            ]
            path.write_text("\n".join(map(json.dumps, records)) + "\n", encoding="utf-8")
            report = analyze([path])
            self.assertEqual(len(report["sessions"]), 2)
            self.assertEqual({s["schema_version"] for s in report["sessions"]}, {1, 2})

    def test_large_gap_excludes_unobserved_kad_events(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "gaps.jsonl"
            records = [
                kad_row("2026-11-26T12:00:00Z", 0),
                kad_row("2026-11-26T12:10:00Z", 500,
                        kad_slots_consumed_cumulative=999),
            ]
            path.write_text("\n".join(map(json.dumps, records)) + "\n", encoding="utf-8")
            session = analyze([path])["sessions"][0]
            self.assertEqual(session["valid_intervals"], 0)
            self.assertEqual(session["kad_cumulative_deltas"]["kad_slots_consumed_cumulative"], 0)
            self.assertIsNone(session["kad_slot_waste_fraction"])


if __name__ == "__main__":
    unittest.main()
