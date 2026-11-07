#!/usr/bin/env python3
"""Static safeguards for reuse of installed eMule directories.

These checks do NOT substitute for runtime verification with a Windows client.
Do not launch installed and portable clients concurrently against one Temp tree.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFS = (ROOT / "srchybrid" / "Preferences.cpp").read_text(encoding="utf-8-sig")
APP = (ROOT / "srchybrid" / "Emule.cpp").read_text(encoding="utf-8-sig")
HEADER = (ROOT / "srchybrid" / "Preferences.h").read_text(encoding="utf-8-sig")


class PortableSharedDirectoryContract(unittest.TestCase):
    def test_portable_loads_saved_incoming_and_temp_routes(self):
        load = PREFS[PREFS.index("void CPreferences::LoadPreferences()"):]
        self.assertIn('m_strIncomingDir = ini.GetString(_T("IncomingDir"), _T(""));', load)
        self.assertIn('CString sTempdirs(ini.GetString(_T("TempDir"), _T("")));', load)
        self.assertIn('sTempdirs.AppendFormat(_T("|%s"), (LPCTSTR)ini.GetString(_T("TempDirs")));', load)
        self.assertIn("GetDefaultDirectory(EMULE_INCOMINGDIR, true)", load)
        self.assertIn("GetDefaultDirectory(EMULE_TEMPDIR, true)", load)
        self.assertNotIn("m_strIncomingDir = IsPortableMode() ?", load)
        self.assertNotIn("CString sTempdirs(IsPortableMode() ?", load)

    def test_portable_saves_paths_with_its_own_preferences(self):
        save = PREFS[PREFS.index("void CPreferences::SavePreferences()"):]
        self.assertIn('ini.WriteString(_T("IncomingDir"), m_strIncomingDir);', save)
        self.assertIn('ini.WriteString(_T("TempDir"), tempdir[0]);', save)
        self.assertIn('ini.WriteString(_T("TempDirs"), CPTR(tempdirs, 1));', save)
        self.assertIn('m_pszProfileName = _tcsdup(sConfDir + PREFINIFILE);', APP)

    def test_startup_rejects_missing_existing_routes(self):
        before_load = APP[:APP.index("thePrefs.Init();")]
        self.assertIn('GetProfileString(_T("eMule"), _T("TempDir"), _T(""))', before_load)
        self.assertIn('GetProfileString(_T("eMule"), _T("TempDirs"), _T(""))', before_load)
        self.assertIn('GetProfileString(_T("eMule"), _T("IncomingDir"), _T(""))', before_load)
        self.assertIn("!::PathIsDirectory(directory)", before_load)
        self.assertIn("!::PathIsDirectory(configuredIncomingDir)", before_load)

    def test_shared_directory_checks_installed_client_and_reserves_mutex(self):
        self.assertIn("FindInstalledEmuleWindow", APP)
        self.assertIn("RegisterWindowMessage(EMULE_GUID)", APP)
        shared = APP[APP.index("thePrefs.Init();"):APP.index("theStats.Init();")]
        self.assertIn("thePrefs.GetTempDirCount()", shared)
        self.assertIn("::EnumWindows(FindInstalledEmuleWindow", shared)
        self.assertIn("::CreateMutex(NULL, FALSE, originalMutexName)", shared)
        self.assertIn("mutexError == ERROR_ALREADY_EXISTS", shared)
        self.assertIn("return FALSE;", shared)
        self.assertIn("::CloseHandle(s_hOriginalEmuleGuard);", APP)
        self.assertIn("GetPortableDefaultDirectory(EMULE_TEMPDIR)", APP)
        self.assertIn("GetPortableDefaultDirectory(EMULE_INCOMINGDIR)", APP)
        self.assertIn("GetPortableDefaultDirectory(EDefaultDirectory eDirectory)", HEADER)
        self.assertNotIn("thePrefs.GetDefaultDirectory(", APP)

    def test_isolation_and_normal_defaults_remain(self):
        self.assertIn("if (IsPortableMode()) {", PREFS)
        self.assertIn('strSelectedDataBaseDirectory += _T("data\\\\");', PREFS)
        self.assertIn("if (CPreferences::IsPortableMode())", APP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
