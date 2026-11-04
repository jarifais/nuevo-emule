#!/usr/bin/env python3
"""Apply the 'Descargar en...' change to eMule Community v0.72a.

This script deliberately uses byte-level, exact-match patches to preserve the
source files' original encoding and line endings. It fails closed if upstream
source code changes in an incompatible way.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "srchybrid"


def patch(name: str, old: str, new: str) -> None:
    path = ROOT / name
    original = path.read_bytes()
    crlf = b"\r\n" in original
    content = original.replace(b"\r\n", b"\n")
    before = old.encode("ascii")
    after = new.encode("ascii")

    if after in content and before not in content:
        print(f"ALREADY {name}")
        return
    count = content.count(before)
    if count != 1:
        raise RuntimeError(f"{name}: expected one anchor, found {count}: {old[:90]!r}")
    updated = content.replace(before, after, 1)
    if crlf:
        updated = updated.replace(b"\n", b"\r\n")
    path.write_bytes(updated)
    print(f"PATCHED {name}")


def main() -> None:
    if not ROOT.is_dir():
        raise SystemExit("Missing srchybrid source directory; import eMule v0.72a first")

    patch(
        "MenuCmds.h",
        "#define MP_UPDATE\t\t\t\t10364\n",
        "#define MP_UPDATE\t\t\t\t10364\n"
        "#define MP_DOWNLOAD_TO_FOLDER\t10365 // nuevo-emule: search result destination\n",
    )

    patch(
        "SearchListCtrl.cpp",
        '#include "SearchResultsWnd.h"\n',
        '#include "SearchResultsWnd.h"\n'
        '#include "TransferWnd.h"\n',
    )

    patch(
        "SearchListCtrl.cpp",
        'm_SearchFileMenu.AppendMenu(MF_STRING, MP_RESUME, GetResString(IDS_DOWNLOAD), _T("Resume"));\n',
        'm_SearchFileMenu.AppendMenu(MF_STRING, MP_RESUME, GetResString(IDS_DOWNLOAD), _T("Resume"));\n'
        '\tm_SearchFileMenu.AppendMenu(MF_STRING, MP_DOWNLOAD_TO_FOLDER, _T("Descargar en..."));\n',
    )

    patch(
        "SearchListCtrl.cpp",
        "m_SearchFileMenu.EnableMenuItem(MP_RESUME, iToDownload > 0 ? MF_ENABLED : MF_GRAYED);\n",
        "m_SearchFileMenu.EnableMenuItem(MP_RESUME, iToDownload > 0 ? MF_ENABLED : MF_GRAYED);\n"
        "\tm_SearchFileMenu.EnableMenuItem(MP_DOWNLOAD_TO_FOLDER, iToDownload > 0 ? MF_ENABLED : MF_GRAYED);\n",
    )

    patch(
        "SearchListCtrl.cpp",
        "\t\tcase MP_RESUME:\n",
        '''\t\tcase MP_DOWNLOAD_TO_FOLDER:
\t\t\t{
\t\t\t\t// Pick one destination for all selected search results. Cancel does nothing.
\t\t\t\tCFolderPickerDialog folderPicker(thePrefs.GetMuleDirectory(EMULE_INCOMINGDIR),
\t\t\t\t\tOFN_PATHMUSTEXIST | OFN_NOCHANGEDIR, this);
\t\t\t\tif (folderPicker.DoModal() != IDOK)
\t\t\t\t\treturn TRUE;

\t\t\t\tCString destination = folderPicker.GetPathName();
\t\t\t\tif (destination.IsEmpty() || destination.GetLength() >= MAX_PATH - 1) {
\t\t\t\t\tAfxMessageBox(GetResString(IDS_ERR_BADFOLDER));
\t\t\t\t\treturn TRUE;
\t\t\t\t}
\t\t\t\tMakeFoldername(destination);
\t\t\t\tif (!PathIsDirectory(destination) || !thePrefs.IsShareableDirectory(destination)) {
\t\t\t\t\tAfxMessageBox(GetResString(IDS_ERR_BADFOLDER));
\t\t\t\t\treturn TRUE;
\t\t\t\t}

\t\t\t\t// eMule already persists a download's category in its .part.met.
\t\t\t\t// Reuse or automatically create a destination category; no new
\t\t\t\t// file-format tags and no extra manual setup are required.
\t\t\t\tint category = -1;
\t\t\t\tfor (int i = 0; i < thePrefs.GetCatCount(); ++i) {
\t\t\t\t\tCString candidate = (i == 0)
\t\t\t\t\t\t? thePrefs.GetMuleDirectory(EMULE_INCOMINGDIR)
\t\t\t\t\t\t: thePrefs.GetCatPath(i);
\t\t\t\t\tMakeFoldername(candidate);
\t\t\t\t\tif (candidate.CompareNoCase(destination) == 0) {
\t\t\t\t\t\tcategory = i;
\t\t\t\t\t\tbreak;
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tif (category < 0) {
\t\t\t\t\tCString title(_T("Destino: "));
\t\t\t\t\ttitle += destination;
\t\t\t\t\tcategory = theApp.emuledlg->transferwnd->AddCategory(
\t\t\t\t\t\ttitle, destination, _T(""), _T(""));
\t\t\t\t\ttheApp.emuledlg->searchwnd->UpdateCatTabs();
\t\t\t\t\tthePrefs.SaveCats();
\t\t\t\t}

\t\t\t\ttheApp.emuledlg->searchwnd->DownloadSelected(
\t\t\t\t\tthePrefs.AddNewFilesPaused(), category);
\t\t\t\treturn TRUE;
\t\t\t}
\t\tcase MP_RESUME:
''',
    )

    patch(
        "SearchDlg.h",
        "\tvoid DownloadSelected(bool bPaused);\n",
        "\tvoid DownloadSelected(bool bPaused);\n"
        "\tvoid DownloadSelected(bool bPaused, int category);\n",
    )

    patch(
        "SearchDlg.cpp",
        "void CSearchDlg::DownloadSelected(bool bPaused)\n{\n\tm_pwndResults->DownloadSelected(bPaused);\n}\n",
        "void CSearchDlg::DownloadSelected(bool bPaused)\n{\n\tm_pwndResults->DownloadSelected(bPaused);\n}\n\n"
        "void CSearchDlg::DownloadSelected(bool bPaused, int category)\n"
        "{\n\tm_pwndResults->DownloadSelected(bPaused, category);\n}\n",
    )

    patch(
        "SearchResultsWnd.h",
        "\tvoid\tDownloadSelected(bool bPaused);\n",
        "\tvoid\tDownloadSelected(bool bPaused);\n"
        "\tvoid\tDownloadSelected(bool bPaused, int category);\n",
    )

    patch(
        "SearchResultsWnd.cpp",
        "void CSearchResultsWnd::DownloadSelected(bool bPaused)\n{\n\tCWaitCursor curWait;\n",
        "void CSearchResultsWnd::DownloadSelected(bool bPaused)\n"
        "{\n\tDownloadSelected(bPaused, GetSelectedCat());\n}\n\n"
        "void CSearchResultsWnd::DownloadSelected(bool bPaused, int category)\n"
        "{\n\tCWaitCursor curWait;\n",
    )

    patch(
        "SearchResultsWnd.cpp",
        "theApp.downloadqueue->AddSearchToDownload(&tempFile, bPaused, GetSelectedCat());",
        "theApp.downloadqueue->AddSearchToDownload(&tempFile, bPaused, category);",
    )

    print("Download-folder patch OK (all 10 anchors checked)")


if __name__ == "__main__":
    main()
