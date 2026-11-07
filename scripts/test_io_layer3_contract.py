#!/usr/bin/env python3
"""Layer 3.1: verify per-check free-space caching without changing decisions.

Static source assertions plus deterministic equivalence of reference and
optimized disk-space decision models. Not a substitute for disk/USB tests.
"""
from pathlib import Path
from random import Random
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / "srchybrid" / "DownloadQueue.cpp").read_text(
    encoding="utf-8-sig"
)
CHECK = SOURCE.split("void CDownloadQueue::CheckDiskspace(bool bNotEnoughSpaceLeft)", 1)[1].split(
    "void CDownloadQueue::GetDownloadSourcesStats(", 1
)[0]
SKIP = {"PS_PAUSED", "PS_ERROR", "PS_COMPLETING", "PS_COMPLETE"}


def check_space(files, folders, available, minimum, disk_full=False, enabled=True, cache=False):
    """Return per-file actions and a count of free-space queries.

    The model deliberately leaves a single Temp directory using its legacy
    one-sample path. For multiple Temp directories, the new implementation
    reuses the first answer for each *actual* .part directory.
    """
    reads = 0
    cache_by_path = {}

    def get_free(path):
        nonlocal reads
        reads += 1
        return available[path]

    decisions = []
    if not enabled:
        for file in files:
            if not disk_full and file["status"] not in SKIP:
                decisions.append((file["id"], "resume_insufficient"))
        return decisions, reads

    single = len(folders) == 1
    main_free = get_free(folders[0]) if single and not disk_full else 0
    for file in files:
        if file["status"] in SKIP:
            continue
        if disk_full:
            free = 0
        elif single:
            free = main_free
        elif cache:
            path = file["tmp"]
            if path not in cache_by_path:
                cache_by_path[path] = get_free(path)
            free = cache_by_path[path]
        else:
            free = get_free(file["tmp"])

        if minimum == 0:
            decisions.append((file["id"], "resume_insufficient" if file["needed"] <= free else "pause"))
        elif free < minimum and (not file["normal"] or file["needed"] > 0):
            decisions.append((file["id"], "pause"))
    return decisions, reads


class Layer3DiskSpaceTests(unittest.TestCase):
    def test_cache_local_to_disk_check_and_keeps_hard_full_signal(self):
        self.assertIn("#include <map>", SOURCE)
        self.assertIn("std::map<CString, uint64, TempPathLess> freeSpaceByTempDir;", CHECK)
        self.assertIn("freeSpaceByTempDir.find(tempPath)", CHECK)
        self.assertIn("freeSpaceByTempDir.insert(std::make_pair(tempPath, freeSpace));", CHECK)
        self.assertIn("const CString tempPath(cur_file->GetTmpPath());", CHECK)
        self.assertIn("left.Compare(right) < 0", CHECK)
        self.assertIn("if (!bNotEnoughSpaceLeft)", CHECK)
        self.assertIn("const uint64 nTotalAvailableSpaceMain = (bNotEnoughSpaceLeft || !singleTempDir)", CHECK)
        self.assertEqual(CHECK.count("GetFreeDiskSpaceX(cur_file->GetTmpPath())"), 0)
        self.assertIn("GetFreeDiskSpaceX(tempPath)", CHECK)

    def test_status_checks_and_pause_resume_remain(self):
        for status in ("PS_PAUSED:", "PS_ERROR:", "PS_COMPLETING:", "PS_COMPLETE:"):
            self.assertIn(status, CHECK)
        self.assertIn("cur_file->ResumeFileInsufficient();", CHECK)
        self.assertIn("cur_file->PauseFile(true);", CHECK)
        self.assertIn("cur_file->IsNormalFile()", CHECK)
        self.assertIn("cur_file->GetNeededSpace()", CHECK)
        self.assertIn("if (!thePrefs.IsCheckDiskspaceEnabled())", CHECK)
        self.assertIn("m_lastcheckdiskspacetime = ::GetTickCount();", CHECK)

    def test_reference_and_cached_decisions_match(self):
        rng = Random(30920261107)
        folders = ["E:\\Temp\\", "E:\\MoreTemp\\", "\\\\server\\share\\Temp\\", "F:\\External\\"]
        for file_count in (0, 1, 15, 1000, 10000):
            files = [
                {
                    "id": i,
                    "tmp": rng.choice(folders),
                    "status": rng.choice(
                        ["PS_PAUSED", "PS_ERROR", "PS_COMPLETING",
                         "PS_COMPLETE", "PS_READY", "PS_EMPTY", "PS_INSUFFICIENT"]
                    ),
                    "normal": bool(rng.randrange(2)),
                    "needed": rng.choice([0, 1, 4096, 20_000_000, 2_000_000_000]),
                }
                for i in range(file_count)
            ]
            space = {f: rng.choice([0, 50, 200_000, 30_000_000, 4_000_000_000]) for f in folders}
            for min_space in (0, 20_000_000):
                for disk_full in (False, True):
                    for enabled in (False, True):
                        for temp_dirs in (folders[:1], folders):
                            original, calls_original = check_space(
                                files, temp_dirs, space, min_space, disk_full, enabled, False
                            )
                            modified, calls_new = check_space(
                                files, temp_dirs, space, min_space, disk_full, enabled, True
                            )
                            self.assertEqual(original, modified)
                            self.assertLessEqual(calls_new, calls_original)
                            if disk_full or not enabled:
                                self.assertEqual(calls_new, 0)
                            elif len(temp_dirs) > 1:
                                self.assertLessEqual(calls_new, len(folders))

    def test_disconnected_usb_is_not_cached_across_passes(self):
        files = [
            {"id": 0, "tmp": "E:\\Temp\\", "status": "PS_READY", "normal": False, "needed": 3},
            {"id": 1, "tmp": "E:\\Temp\\", "status": "PS_READY", "normal": False, "needed": 3},
        ]
        up, reads = check_space(files, ["E:\\Temp\\", "F:\\Temp\\"],
                                {"E:\\Temp\\": 100, "F:\\Temp\\": 0}, 0, cache=True)
        down, reads_down = check_space(files, ["E:\\Temp\\", "F:\\Temp\\"],
                                     {"E:\\Temp\\": 0, "F:\\Temp\\": 0}, 0, cache=True)
        self.assertEqual(up, [(0, "resume_insufficient"), (1, "resume_insufficient")])
        self.assertEqual(down, [(0, "pause"), (1, "pause")])
        self.assertEqual((reads, reads_down), (1, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
