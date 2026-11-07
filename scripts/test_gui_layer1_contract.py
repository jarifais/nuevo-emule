#!/usr/bin/env python3
"""Static regression checks for download-list performance and safety.

This is a source contract, NOT a functional Windows GUI benchmark. MSBuild,
manual use with 10,000 files, and recovery tests remain necessary.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "srchybrid" / "DownloadListCtrl.cpp").read_text(encoding="utf-8-sig")
HEADER = (ROOT / "srchybrid" / "DownloadListCtrl.h").read_text(encoding="utf-8-sig")
PARTFILE = (ROOT / "srchybrid" / "PartFile.h").read_text(encoding="utf-8-sig")
MULE = (ROOT / "srchybrid" / "MuleListCtrl.cpp").read_text(encoding="utf-8-sig")
QUEUE = (ROOT / "srchybrid" / "DownloadQueue.cpp").read_text(encoding="utf-8-sig")


def body(start: str, end: str) -> str:
    first = CPP.find(start)
    last = CPP.find(end, first + len(start))
    if first < 0 or last < 0:
        raise AssertionError(f"Missing or reordered function bounds: {start!r}")
    return CPP[first:last]


class DownloadListLayer1Contract(unittest.TestCase):
    def test_fast_row_data_preserves_debug_equivalence(self):
        self.assertIn("DWORD_PTR GetItemData(int iItem)", HEADER)
        self.assertIn("CListCtrl::GetItemData(iItem)", HEADER)
        self.assertIn("ASSERT(rowData == CMuleListCtrl::GetItemData(iItem))", HEADER)
        self.assertIn("#ifdef _DEBUG", HEADER)

    def test_add_file_does_not_count_failed_insertions(self):
        fn = body("void CDownloadListCtrl::AddFile(", "void CDownloadListCtrl::AddSource(")
        self.assertRegex(
            fn,
            r"if \(InsertItem\([^;]+\) >= 0\)\s*\+\+m_nVisibleFileCount;",
        )

    def test_category_switch_does_not_find_every_file(self):
        fn = body("void CDownloadListCtrl::ChangeCategory(", "void CDownloadListCtrl::HideFile(")
        self.assertIn("std::unordered_set", fn)
        self.assertIn("GetItemData(i)", fn)
        self.assertIn("owner->srcarevisible = false", fn)
        self.assertNotIn("ShowFile(it)", fn)
        self.assertNotIn("HideFile(it)", fn)
        self.assertNotIn("FindItem(", fn)
        self.assertIn("m_nVisibleFileCount = visibleFileCount;", fn)
        self.assertIn("ReportVisibleFileCount();", fn)
        self.assertIn("++visibleFileCount;", fn)
        self.assertNotIn("ShowFilesCount();", fn)

    def test_source_collapse_cleans_all_rows_not_only_contiguous(self):
        fn = body("void CDownloadListCtrl::HideSources(", "void CDownloadListCtrl::ExpandCollapseItem(")
        self.assertIn("for (int i = GetItemCount(); --i >= 0;)", fn)
        self.assertIn("item->owner == toCollapse", fn)
        self.assertIn("DeleteItem(i);", fn)
        self.assertIn("toCollapse->srcarevisible = false;", fn)

    def test_hidden_sources_and_categories_do_not_trigger_visual_search(self):
        fn = body("void CDownloadListCtrl::UpdateItem(", "void CDownloadListCtrl::DrawFileItem(")
        self.assertLess(fn.index("!updateItem->owner->srcarevisible"), fn.index("FindItem(&find)"))
        self.assertLess(fn.index("!partfile->CheckShowItemInGivenCat(m_curTab)"), fn.index("FindItem(&find)"))
        self.assertIn("CPartFile *partfile = static_cast<CPartFile*>", fn)
        self.assertIn("bool\tCheckShowItemInGivenCat(INT_PTR inCategory) /*const*/;", PARTFILE)

    def test_source_removal_is_batched_and_safe(self):
        fn = body("void CDownloadListCtrl::RemoveSource(", "bool CDownloadListCtrl::RemoveFile(")
        self.assertIn("std::unordered_set", fn)
        self.assertIn("owner == NULL || owner == item->owner", fn)
        self.assertIn("m_ListItems.lower_bound(source)", fn)
        self.assertIn("for (int i = GetItemCount(); --i >= 0;)", fn)
        self.assertNotIn("FindItem(", fn)
        self.assertLess(fn.index("it = m_ListItems.erase(it)"), fn.index("DeleteItem(i)"))
        self.assertLess(fn.index("DeleteItem(i)"), fn.index("delete *it"))
        self.assertIn("SetRedraw(false);", fn)
        self.assertIn("SetRedraw(true);", fn)

    def test_removal_unlinks_then_removes_rows_then_frees_memory(self):
        fn = body("bool CDownloadListCtrl::RemoveFile(", "void CDownloadListCtrl::UpdateItem(")
        self.assertIn("std::unordered_set", fn)
        self.assertLess(fn.index("it = m_ListItems.erase(it)"), fn.index("DeleteItem(i)"))
        self.assertLess(fn.index("DeleteItem(i)"), fn.index("delete *it"))
        self.assertIn("SetRedraw(false);", fn)
        self.assertIn("SetRedraw(true);", fn)
        self.assertIn("ReportVisibleFileCount();", fn)
        self.assertIn("if (DeleteItem(i) && isFile)", fn)
        self.assertIn("m_nVisibleFileCount - removedVisibleFiles", fn)
        self.assertNotIn("ShowFilesCount();", fn)

    def test_multiselect_state_does_not_redraw_neighbours(self):
        fn = body("void CDownloadListCtrl::OnListModified(", "int CDownloadListCtrl::Compare(")
        self.assertIn("pNMHDR->code == LVN_ITEMCHANGED", fn)
        self.assertIn("pNMListView->uChanged == LVIF_STATE", fn)
        self.assertLess(fn.index("return;"), fn.index("RedrawItems("))
        self.assertIn("if (item < 0 || item >= itemCount)", fn)

    def test_expansion_uses_owner_index_and_rolls_back_partial_insert(self):
        self.assertIn("#include <unordered_map>", HEADER)
        self.assertIn("std::unordered_multimap<CPartFile*, CtrlItem_Struct*>", HEADER)
        fn = body("void CDownloadListCtrl::ExpandCollapseItem(", "void CDownloadListCtrl::OnLvnItemActivate(")
        self.assertIn("m_SourcesByOwner.equal_range(partfile)", fn)
        self.assertIn("if (insertionFailed && partfile->srcarevisible)", fn)
        self.assertIn("HideSources(partfile);", fn)
        self.assertNotIn("for (ListItems::const_iterator it = m_ListItems.begin()", fn)

    def test_owner_index_tracks_creation_and_all_removal_paths(self):
        add = body("void CDownloadListCtrl::AddSource(", "void CDownloadListCtrl::RemoveSource(")
        self.assertIn("m_SourcesByOwner.emplace(owner, newitem);", add)
        remove_source = body("void CDownloadListCtrl::RemoveSource(", "bool CDownloadListCtrl::RemoveFile(")
        self.assertIn("m_SourcesByOwner.equal_range(item->owner)", remove_source)
        self.assertLess(remove_source.index("m_SourcesByOwner.erase(ownerIt)"),
                        remove_source.index("delete *it;"))
        remove_file = body("bool CDownloadListCtrl::RemoveFile(", "void CDownloadListCtrl::UpdateItem(")
        self.assertLess(remove_file.index("m_SourcesByOwner.erase("), remove_file.index("delete *it;"))
        clear = body("void CDownloadListCtrl::ClearCompleted(int", "void CDownloadListCtrl::SetStyle(")
        self.assertLess(clear.index("m_SourcesByOwner.erase("), clear.index("delete *it;"))
        self.assertIn("m_SourcesByOwner.clear();", CPP)

    def test_startup_batches_caption_updates_but_interactive_adds_notify(self):
        add = body("void CDownloadListCtrl::AddFile(", "void CDownloadListCtrl::AddSource(")
        self.assertIn("if (bNotifyCount)", add)
        self.assertIn("ReportVisibleFileCount();", add)
        self.assertIn("bNotifyCount = true", HEADER)
        initialize = QUEUE.split("void CDownloadQueue::Init()", 1)[1].split(
            "CDownloadQueue::~CDownloadQueue()", 1
        )[0]
        self.assertEqual(initialize.count("GetDownloadList().AddFile(toadd, false)"), 2)
        self.assertEqual(initialize.count("GetDownloadList().ReportVisibleFileCount()"), 1)

    def test_clear_completed_uses_one_batch_and_direct_lookup(self):
        fn = body("void CDownloadListCtrl::ClearCompleted(int", "void CDownloadListCtrl::SetStyle(")
        self.assertIn("std::unordered_set<const CPartFile*> completed;", fn)
        self.assertIn("std::unordered_set<const CtrlItem_Struct*> removeItems;", fn)
        self.assertIn("for (int i = GetItemCount(); --i >= 0;)", fn)
        self.assertIn("m_SourcesByOwner.erase(", fn)
        self.assertLess(fn.index("it = m_ListItems.erase(it)"), fn.index("DeleteItem(i)"))
        self.assertLess(fn.index("DeleteItem(i)"), fn.index("delete *it"))
        self.assertNotIn("if (RemoveFile(file))", fn)
        self.assertIn("m_ListItems.find(const_cast<CPartFile*>(pFile))", fn)

    def test_selection_command_scans_are_coalesced(self):
        fn = CPP.split("bool CDownloadListCtrl::ReportAvailableCommands(", 1)[1]
        self.assertIn("const DWORD elapsed = curTick - m_dwLastAvailableCommandsCheck;", fn)
        self.assertIn("m_availableCommandsDirty ? 200u : SEC2MS(3)", fn)

    def test_source_tree_painting_checks_next_row_and_owner(self):
        fn = body("void CDownloadListCtrl::DrawItem(", "void CDownloadListCtrl::HideSources(")
        self.assertIn("nextItem != NULL", fn)
        self.assertIn("nextItem->owner ==", fn)

    def test_scroll_end_releases_device_context_and_checks_empty_list(self):
        first = MULE.index("void CMuleListCtrl::OnLvnEndScrollList(")
        last = MULE.index("void CMuleListCtrl::InitItemMemDC(", first)
        fn = MULE[first:last]
        self.assertIn("iLast >= 0", fn)
        self.assertIn("GetItemRect(iLast, &rcItem, LVIR_BOUNDS) &&", fn)
        self.assertIn("CClientDC dc(this)", fn)
        self.assertNotIn("GetDC()->", fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
