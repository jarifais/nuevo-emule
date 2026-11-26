import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lab_experiment.py"
spec = importlib.util.spec_from_file_location("lab_experiment", SCRIPT)
lab = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lab
spec.loader.exec_module(lab)


class LabExperimentTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime.fromisoformat("2026-12-01T00:00:00+01:00")
        self.plan = lab.build_plan(self.start)

    def test_deterministic_balanced_plan(self):
        self.assertEqual(self.plan, lab.build_plan(self.start))
        lab.validate_plan(self.plan)
        self.assertEqual(len(self.plan["blocks"]), 24)
        self.assertEqual(sum(b["arm"] == "baseline" for b in self.plan["blocks"]), 12)
        self.assertTrue(all(sum(b["arm"] == f for b in self.plan["blocks"]) == 3 for f in lab.FLAGS))
        for slot in range(4):
            self.assertEqual(sum(b["arm"] == "baseline" and b["time_slot"] == slot
                                 for b in self.plan["blocks"]), 3)

    def test_plan_rejects_misaligned_flag(self):
        self.plan["blocks"][0]["flags"]["kad_01"] = 1
        with self.assertRaises(ValueError):
            lab.validate_plan(self.plan)

    def test_reject_naive_datetime(self):
        with self.assertRaises(ValueError):
            lab.build_plan(datetime(2026, 12, 1))

    def test_no_data_is_inconclusive(self):
        report = lab.analyze(self.plan, [])
        self.assertEqual(report["valid_blocks"], 0)
        self.assertTrue(all(c["evidence_grade"] == "insufficient" for c in report["comparisons"].values()))
        self.assertFalse(report["automatic_decision"])

    def test_reject_unacknowledged_and_invalid_flags(self):
        block = self.plan["blocks"][0]
        ts = lab.utc_iso(lab.parse_utc(block["warmup_end_utc"]) + timedelta(seconds=60))
        template = {"block_id": block["block_id"], "timestamp_utc": ts,
                    "applied_flags": block["flags"], "profile_acknowledged": True,
                    "experiment_id": self.plan["experiment_id"], "build_id": "test-sha-123",
                    "telemetry_healthy": True, **{m: 0 for m in lab.METRICS}}
        unacked = dict(template, profile_acknowledged=False)
        invalid = dict(template, applied_flags={f: 1 for f in lab.FLAGS})
        report = lab.analyze(self.plan, [unacked, invalid])
        self.assertEqual(report["invalid_sample_count"], 2)
        self.assertEqual(report["valid_blocks"], 0)

    def test_discard_warmup_and_duplicates(self):
        b = self.plan["blocks"][0]
        sample = {"block_id": b["block_id"], "timestamp_utc": b["start_utc"],
                  "applied_flags": b["flags"], "profile_acknowledged": True,
                  "experiment_id": self.plan["experiment_id"], "build_id": "test-sha-123",
                  "telemetry_healthy": True, **{m: 5 for m in lab.METRICS}}
        mid = dict(sample, timestamp_utc=lab.utc_iso(lab.parse_utc(b["warmup_end_utc"]) + timedelta(seconds=60)))
        report = lab.analyze(self.plan, [sample, mid, mid])
        self.assertEqual(report["invalid_sample_count"], 1)
        self.assertEqual(report["blocks"][0]["valid_samples"], 1)
        self.assertEqual(report["blocks"][0]["download_bytes_per_minute"], 5)

    def test_reject_mixed_builds(self):
        b = self.plan["blocks"][0]
        a = {"block_id": b["block_id"], "timestamp_utc": b["warmup_end_utc"],
             "experiment_id": self.plan["experiment_id"], "build_id": "sha1",
             "applied_flags": b["flags"], "profile_acknowledged": True,
             "telemetry_healthy": True, **{m: 0 for m in lab.METRICS}}
        other = dict(a, build_id="sha2")
        with self.assertRaises(ValueError):
            lab.analyze(self.plan, [a, other])

    def test_full_synthetic_data_and_preliminary_not_accept(self):
        samples = []
        for b in self.plan["blocks"]:
            for minute in range(30, 360):
                ts = lab.utc_iso(lab.parse_utc(b["start_utc"]) + timedelta(minutes=minute))
                samples.append({"block_id": b["block_id"], "timestamp_utc": ts,
                                "applied_flags": b["flags"], "profile_acknowledged": True,
                                "experiment_id": self.plan["experiment_id"], "build_id": "test-sha-123",
                                "telemetry_healthy": True,
                                **{metric: (120 if b["arm"] == "kad_01" else 100)
                                   for metric in lab.METRICS}})
        report = lab.analyze(self.plan, samples)
        self.assertEqual(report["valid_blocks"], 24)
        self.assertEqual(report["invalid_sample_count"], 0)
        self.assertEqual(report["comparisons"]["kad_01"]["relative_effects"]["download_bytes_relative_percent"], 20)
        self.assertEqual(report["comparisons"]["kad_01"]["decision"], "inconclusive_no_automatic_adoption")


if __name__ == "__main__":
    unittest.main()
