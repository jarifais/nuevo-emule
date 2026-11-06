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

    def test_category_switch_does_not_find_every_file(self):
        fn = body("void CDownloadListCtrl::ChangeCategory(", "void CDownloadListCtrl::HideFile(")
        self.assertIn("std::unordered_set", fn)
        self.assertIn("GetItemData(i)", fn)
        self.assertIn("owner->srcarevisible = false", fn)
        self.assertNotIn("ShowFile(it)", fn)
        self.assertNotIn("HideFile(it)", fn)
        self.assertNotIn("FindItem(", fn)
        self.assertIn("ShowFilesCount();", fn)

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

    def test_removal_unlinks_then_removes_rows_then_frees_memory(self):
        fn = body("bool CDownloadListCtrl::RemoveFile(", "void CDownloadListCtrl::UpdateItem(")
        self.assertIn("std::unordered_set", fn)
        self.assertLess(fn.index("it = m_ListItems.erase(it)"), fn.index("DeleteItem(i)"))
        self.assertLess(fn.index("DeleteItem(i)"), fn.index("delete *it"))
        self.assertIn("SetRedraw(false);", fn)
        self.assertIn("SetRedraw(true);", fn)
        self.assertIn("ShowFilesCount();", fn)

    def test_multiselect_state_does_not_redraw_neighbours(self):
        fn = body("void CDownloadListCtrl::OnListModified(", "int CDownloadListCtrl::Compare(")
        self.assertIn("pNMHDR->code == LVN_ITEMCHANGED", fn)
        self.assertIn("pNMListView->uChanged == LVIF_STATE", fn)
        self.assertLess(fn.index("return;"), fn.index("RedrawItems("))
        self.assertIn("if (item < 0 || item >= itemCount)", fn)

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
