#!/usr/bin/env python3
"""Layer 2.1: static code contracts and deterministic local-request ordering model.

These tests do not measure wall-clock acceleration or replace Windows runtime QA.
"""
from pathlib import Path
from random import Random
import unittest

ROOT = Path(__file__).resolve().parents[1]
QUEUE = (ROOT / "srchybrid" / "DownloadQueue.cpp").read_text(encoding="utf-8-sig")
PART = (ROOT / "srchybrid" / "PartFile.cpp").read_text(encoding="utf-8-sig")
HEADER = (ROOT / "srchybrid" / "PartFile.h").read_text(encoding="utf-8-sig")
MAX_SCORE = 0xFFFFFFFF


def request_score(item):
    priority = 0 if item["priority"] >= 2 else 2 - item["priority"]
    return (item["last"] + priority) & MAX_SCORE


def legacy_batch(items, limit=15):
    """Reference simulation of the original repeated min scan.

    The original loop would not terminate when all eligible scores are
    MAX_SCORE; the model treats that condition as having no selectable item.
    """
    queue = list(enumerate(items))
    sent = []
    while queue and len(sent) < limit:
        queue = [(index, item) for index, item in queue if item["valid"]]
        candidate = None
        best = MAX_SCORE
        for index, item in queue:
            score = request_score(item)
            if score < best:
                candidate, best = index, score
        if candidate is None:
            break
        selected = next(item for index, item in queue if index == candidate)
        queue = [(index, item) for index, item in queue if index != candidate]
        if selected["supported"]:
            sent.append(candidate)
    return sent, [index for index, _ in queue]


def optimized_batch(items, limit=15):
    """Stable sort of eligible queue positions and single-pass selection."""
    queue = [(index, item) for index, item in enumerate(items) if item["valid"]]
    candidates = sorted(
        ((request_score(item), index, item) for index, item in queue
         if request_score(item) != MAX_SCORE),
        key=lambda entry: entry[0],
    )
    sent = []
    removed = set()
    for _score, index, item in candidates:
        if len(sent) >= limit:
            break
        removed.add(index)
        if item["supported"]:
            sent.append(index)
    return sent, [index for index, _ in queue if index not in removed]


class SchedulerLayer21Contracts(unittest.TestCase):
    def test_active_processing_still_runs_every_tick(self):
        process = QUEUE.split("void CDownloadQueue::Process()", 1)[1].split(
            "CPartFile* CDownloadQueue::GetFileNext(", 1
        )[0]
        self.assertIn("if (inSet(fileStatus, PS_READY, PS_EMPTY))", process)
        self.assertIn("datarateX += cur_file->Process(factor, m_udcounter);", process)
        self.assertIn("const bool maintainInactiveFiles = m_udcounter >= 10;", process)
        self.assertIn("maintainInactiveFiles ? time(NULL) : 0;", process)
        self.assertIn("cur_file->StopPausedFile(inactiveMaintenanceTime);", process)
        self.assertIn("theStats.m_fGlobalDone += (float)cur_file->GetCompletedSize();", process)

    def test_inactive_purge_reuses_clock_and_preserves_deferred_delete(self):
        self.assertIn("void\tStopPausedFile(time_t currentTime = 0);", HEADER)
        part = PART.split("void CPartFile::StopPausedFile(time_t currentTime)", 1)[1].split(
            "void CPartFile::", 1
        )[0]
        self.assertIn("if (currentTime == 0)", part)
        self.assertIn("currentTime = time(NULL);", part)
        self.assertIn("currentTime >= m_iLastPausePurge + HR2S(1)", part)
        self.assertIn("else if (m_bDelayDelete)", part)
        self.assertIn("DeletePartFile();", part)

    def test_local_server_request_uses_one_scan_and_stable_order(self):
        fn = QUEUE.split("void CDownloadQueue::ProcessLocalRequests()", 1)[1].split(
            "void CDownloadQueue::SendLocalSrcRequest(", 1
        )[0]
        self.assertIn("std::vector<RequestCandidate> candidates;", fn)
        self.assertIn("std::stable_sort(candidates.begin(), candidates.end()", fn)
        self.assertIn("return left.score < right.score;", fn)
        self.assertIn("if (score != _UI32_MAX)", fn)
        self.assertEqual(fn.count("m_localServerReqQueue.GetHeadPosition()"), 1)
        self.assertNotIn("while (!m_localServerReqQueue.IsEmpty()", fn)
        self.assertIn("iFiles < iMaxFilesPerTcpFrame", fn)
        self.assertIn("m_localServerReqQueue.RemoveAt(candidates[i].position);", fn)
        self.assertIn("if (status != PS_READY && status != PS_EMPTY)", fn)
        self.assertIn("SupportsLargeFilesTCP()", fn)
        self.assertIn("dataTcpFrame.Write(packet.GetPacket()", fn)

    def test_ordering_with_ties_unsupported_files_and_invalid_states(self):
        rng = Random(20261107)
        for n in (0, 1, 5, 15, 16, 50, 200, 1000):
            for _ in range(10):
                items = [
                    {
                        "priority": rng.randrange(3),
                        "last": rng.choice([0, 5, 5, 10, MAX_SCORE - 1, MAX_SCORE]),
                        "valid": rng.randrange(10) != 0,
                        "supported": rng.randrange(7) != 0,
                    }
                    for _ in range(n)
                ]
                self.assertEqual(legacy_batch(items), optimized_batch(items))

    def test_large_queue_has_bounded_packet_size(self):
        items = [
            {"priority": 1, "last": i % 17, "valid": True, "supported": True}
            for i in range(10000)
        ]
        selected, remaining = optimized_batch(items)
        self.assertEqual(len(selected), 15)
        self.assertEqual(len(remaining), 9985)
        self.assertEqual((selected, remaining), legacy_batch(items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
