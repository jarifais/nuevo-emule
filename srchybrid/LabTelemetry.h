// eMule laboratory: phase-1 low-frequency local metrics (no protocol changes).
// Included only from DownloadQueue.cpp; no project-file changes required.
#pragma once

#include <windows.h>

namespace LabTelemetry
{
    enum { SAMPLE_PERIOD_MS = 60000, MAX_LOG_BYTES = 8 * 1024 * 1024 };

    struct KadEventCounters {
        DWORD slots_consumed;
        DWORD slots_wasted_active_search;
        DWORD lookups_started;
        DWORD lookups_prepare_failed;
        DWORD source_candidates;
        DWORD new_sources_accepted;
    };

    // Process-wide atomic counters. Never store filenames, IPs or file hashes.
    void CountKadSlotConsumed();
    void CountKadSlotWastedActiveSearch();
    void CountKadLookupStarted();
    void CountKadLookupPrepareFailed();
    void CountKadSourceCandidate();
    void CountKadNewSourceAccepted();
    KadEventCounters ReadKadCounters();

    struct Snapshot {
        DWORD tick_ms;
        DWORD elapsed_ms;
        DWORD rate_bytes_per_second;
        DWORD files_total;
        DWORD files_active;
        DWORD files_downloading;
        ULONGLONG listed_sources;
        ULONGLONG transferring_clients;
        ULONGLONG session_received_bytes;
        ULONGLONG kad_down_overhead_bytes;
        ULONGLONG kad_up_overhead_bytes;
        ULONGLONG server_down_overhead_bytes;
        KadEventCounters kad;
    };

    // The download queue runs on the application thread. Only inspect sources
    // on a due tick, not on every 100-ms processing pass.
    inline bool IsSampleDue(DWORD now, DWORD& elapsed_ms)
    {
        static bool sampled = false;
        static DWORD previous = 0;
        elapsed_ms = sampled ? static_cast<DWORD>(now - previous) : 0;
        if (sampled && elapsed_ms < SAMPLE_PERIOD_MS)
            return false;
        sampled = true;
        previous = now;
        return true;
    }

    // One small write per minute. This phase deliberately does not pretend
    // to implement the full A/B schema, feature toggles or Kad event metrics.
    inline bool AppendSnapshot(const CString& log_directory, const Snapshot& s)
    {
        if (log_directory.IsEmpty())
            return false;

        CString directory(log_directory);
        const TCHAR final_char = directory[directory.GetLength() - 1];
        if (final_char != _T('\\') && final_char != _T('/'))
            directory += _T('\\');

        const CString current_path = directory + _T("lab-telemetry-v1.jsonl");
        const CString previous_path = directory + _T("lab-telemetry-v1.previous.jsonl");

        WIN32_FILE_ATTRIBUTE_DATA info = {};
        if (::GetFileAttributesEx(current_path, GetFileExInfoStandard, &info)) {
            ULARGE_INTEGER size = {};
            size.LowPart = info.nFileSizeLow;
            size.HighPart = info.nFileSizeHigh;
            if (size.QuadPart >= MAX_LOG_BYTES) {
                if (!::MoveFileEx(current_path, previous_path, MOVEFILE_REPLACE_EXISTING))
                    return false;
            }
        }

        SYSTEMTIME utc = {};
        ::GetSystemTime(&utc);
        static SYSTEMTIME first_utc = {};
        static bool first_sample = true;
        if (first_sample) {
            first_utc = utc;
            first_sample = false;
        }

        // No filenames, hashes, IP addresses, ports, paths or peer identifiers.
        // Every record represents a snapshot; cumulative counters are NOT
        // per-minute deltas (an analyzer must difference within a session).
        CStringA record;
        record.Format(
            "{\"schema_version\":2,\"record_type\":\"download_queue_snapshot\","
            "\"mode\":\"telemetry_only_no_feature_flags\","
            "\"session_id\":\"%08lX-%04u%02u%02uT%02u%02u%02uZ\","
            "\"timestamp_utc\":\"%04u-%02u-%02uT%02u:%02u:%02uZ\","
            "\"tick_ms_mod_2pow32\":%lu,\"elapsed_since_previous_ms\":%lu,"
            "\"download_rate_bytes_per_second\":%lu,"
            "\"files_total\":%lu,\"files_active\":%lu,"
            "\"files_downloading\":%lu,\"sources_listed_total\":%I64u,"
            "\"clients_transferring_total\":%I64u,"
            "\"session_received_bytes\":%I64u,"
            "\"kad_down_overhead_bytes_cumulative\":%I64u,"
            "\"kad_up_overhead_bytes_cumulative\":%I64u,"
            "\"server_down_overhead_bytes_cumulative\":%I64u,"
            "\"kad_slots_consumed_cumulative\":%lu,"
            "\"kad_slots_wasted_active_search_cumulative\":%lu,"
            "\"kad_lookups_started_cumulative\":%lu,"
            "\"kad_lookups_prepare_failed_cumulative\":%lu,"
            "\"kad_source_candidates_cumulative\":%lu,"
            "\"kad_new_sources_accepted_cumulative\":%lu}\r\n",
            static_cast<unsigned long>(::GetCurrentProcessId()),
            first_utc.wYear, first_utc.wMonth, first_utc.wDay,
            first_utc.wHour, first_utc.wMinute, first_utc.wSecond,
            utc.wYear, utc.wMonth, utc.wDay, utc.wHour, utc.wMinute, utc.wSecond,
            static_cast<unsigned long>(s.tick_ms),
            static_cast<unsigned long>(s.elapsed_ms),
            static_cast<unsigned long>(s.rate_bytes_per_second),
            static_cast<unsigned long>(s.files_total),
            static_cast<unsigned long>(s.files_active),
            static_cast<unsigned long>(s.files_downloading),
            s.listed_sources, s.transferring_clients, s.session_received_bytes,
            s.kad_down_overhead_bytes, s.kad_up_overhead_bytes,
            s.server_down_overhead_bytes,
            static_cast<unsigned long>(s.kad.slots_consumed),
            static_cast<unsigned long>(s.kad.slots_wasted_active_search),
            static_cast<unsigned long>(s.kad.lookups_started),
            static_cast<unsigned long>(s.kad.lookups_prepare_failed),
            static_cast<unsigned long>(s.kad.source_candidates),
            static_cast<unsigned long>(s.kad.new_sources_accepted));

        const HANDLE handle = ::CreateFile(current_path, FILE_APPEND_DATA,
            FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        if (handle == INVALID_HANDLE_VALUE)
            return false;

        DWORD written = 0;
        const DWORD expected = static_cast<DWORD>(record.GetLength());
        const BOOL success = ::WriteFile(handle, (LPCSTR)record, expected, &written, NULL);
        ::CloseHandle(handle);
        return success && written == expected;
    }
} // namespace LabTelemetry
