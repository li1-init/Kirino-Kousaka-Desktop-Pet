namespace KirinoDesktopPet;

using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text.Json;

internal static class CodexActivityMonitor
{
    private static readonly TimeSpan RecentWriteWindow = TimeSpan.FromMinutes(10);
    private const int SessionTailBytes = 256 * 1024;

    public static CodexActivity ReadActivity(DateTimeOffset since)
    {
        try
        {
            if (!HasRunningCodexProcess())
            {
                return CodexActivity.Empty;
            }
            var home = Environment.GetEnvironmentVariable("CODEX_HOME");
            if (string.IsNullOrWhiteSpace(home))
            {
                home = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".codex");
            }
            return ReadActivity(home, DateTime.UtcNow, since);
        }
        catch (Exception error) when (IsFileError(error) || error is Win32Exception
                                      or InvalidOperationException or ArgumentException)
        {
            return CodexActivity.Empty;
        }
    }

    internal static CodexActivity ReadActivity(string codexHome, DateTime now, DateTimeOffset since)
    {
        var cutoff = now - RecentWriteWindow;
        var locks = ReadBusyLocks(Path.Combine(codexHome, "thread-writer-locks"));
        var latest = new Dictionary<Guid, (string Path, DateTime LastWriteUtc)>();
        var sessionRoot = Path.Combine(codexHome, "sessions");
        var completions = new List<CodexCompletion>();
        var active = false;
        foreach (var file in EnumerateFiles(sessionRoot, "*.jsonl", recurse: true))
        {
            var stem = Path.GetFileNameWithoutExtension(file);
            var threadId = Guid.Empty;
            var hasThreadId = stem.Length >= 36 &&
                              Guid.TryParseExact(stem.AsSpan(stem.Length - 36), "D", out threadId);
            try
            {
                var writeTime = File.GetLastWriteTimeUtc(file);
                if (writeTime < cutoff && !locks.ContainsKey(threadId))
                {
                    continue;
                }
                if (hasThreadId)
                {
                    if (!latest.TryGetValue(threadId, out var previous) || writeTime > previous.LastWriteUtc)
                    {
                        latest[threadId] = (file, writeTime);
                    }
                }
                else
                {
                    active |= ReadLatestActivity(file, file, since, completions) == true;
                }
            }
            catch (Exception error) when (IsFileError(error))
            {
                // Files can be rotated or become inaccessible during a scan.
            }
        }

        foreach (var (id, session) in latest)
        {
            var sessionActive = ReadLatestActivity(session.Path, id.ToString("D"), since, completions);
            active |= sessionActive == true || (sessionActive is null && locks.GetValueOrDefault(id) >= cutoff);
        }
        active |= locks.Any(entry => entry.Value >= cutoff && !latest.ContainsKey(entry.Key));
        return new CodexActivity(active, completions);
    }

    private static bool HasRunningCodexProcess()
    {
        var processes = Process.GetProcessesByName("codex");
        try
        {
            return processes.Any(process => !process.HasExited);
        }
        finally
        {
            foreach (var process in processes)
            {
                process.Dispose();
            }
        }
    }

    private static Dictionary<Guid, DateTime> ReadBusyLocks(string folder)
    {
        var locks = new Dictionary<Guid, DateTime>();
        foreach (var file in EnumerateFiles(folder, "*.lock", recurse: false))
        {
            if (!Guid.TryParseExact(Path.GetFileNameWithoutExtension(file), "D", out var id))
            {
                continue;
            }
            try
            {
                using var unused = new FileStream(file, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
            }
            catch (IOException error) when ((error.HResult & 0xFFFF) is 32 or 33)
            {
                locks[id] = File.GetLastWriteTimeUtc(file);
            }
            catch (Exception error) when (IsFileError(error))
            {
                // Lack of access is not evidence of a held writer lock.
            }
        }
        return locks;
    }

    private static string[] EnumerateFiles(string folder, string pattern, bool recurse)
    {
        try
        {
            return Directory.GetFiles(folder, pattern, new EnumerationOptions
            {
                IgnoreInaccessible = true,
                RecurseSubdirectories = recurse,
                AttributesToSkip = FileAttributes.ReparsePoint
            });
        }
        catch (Exception error) when (IsFileError(error))
        {
            return [];
        }
    }

    private static bool? ReadLatestActivity(
        string file, string thread, DateTimeOffset since, List<CodexCompletion> completions)
    {
        bool? active = null;
        bool? legacySignal = null;
        string? activeTurn = null;
        try
        {
            using var stream = new FileStream(file, FileMode.Open, FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete);
            var start = Math.Max(0, stream.Length - SessionTailBytes);
            if (start > 0)
            {
                stream.Position = start - 1;
            }
            var atLineStart = start == 0 || stream.ReadByte() == '\n';
            using var reader = new StreamReader(stream);
            if (!atLineStart)
            {
                reader.ReadLine();
            }
            while (reader.ReadLine() is { } line)
            {
                try
                {
                    using var document = JsonDocument.Parse(line);
                    var record = document.RootElement;
                    switch (GetString(record, "type"))
                    {
                        case "event_msg" when record.TryGetProperty("payload", out var payload):
                            var eventType = GetString(payload, "type");
                            var turnId = GetString(payload, "turn_id") ?? GetString(payload, "root_turn_id");
                            switch (eventType)
                            {
                                case "task_started" or "turn_started":
                                    active = true;
                                    activeTurn = turnId;
                                    break;
                                case "task_complete" or "turn_aborted" or "turn_completed" or
                                     "turn_complete" or "turn_failed" or "task_failed":
                                    if (activeTurn is null || turnId is null || activeTurn == turnId)
                                    {
                                        active = false;
                                        activeTurn = null;
                                    }
                                    var outcome = GetOutcome(eventType, payload);
                                    if (outcome is not null && TryGetTimestamp(record, payload, out var endedAt)
                                        && endedAt >= since)
                                    {
                                        completions.Add(new CodexCompletion(
                                            (thread, turnId ?? endedAt.ToString("O")), endedAt, outcome.Value));
                                    }
                                    break;
                                case "item_started" or "item_completed":
                                    legacySignal = true;
                                    break;
                            }
                            break;
                        case "response_item":
                            legacySignal = true;
                            break;
                    }
                }
                catch (JsonException)
                {
                    // The last line can be incomplete while Codex is writing it.
                }
            }
        }
        catch (Exception error) when (IsFileError(error))
        {
            return null;
        }
        return active ?? legacySignal;
    }

    private static CodexOutcome? GetOutcome(string eventType, JsonElement payload)
    {
        var status = GetString(payload, "status");
        var reason = GetString(payload, "reason");
        if (status is "interrupted" or "cancelled" or "canceled"
            || (eventType == "turn_aborted" && reason is "interrupted" or "replaced" or "budget_limited"))
        {
            return null;
        }
        if (eventType is "turn_failed" or "task_failed" || status is "failed" or "error"
            || (payload.TryGetProperty("error", out var error) && error.ValueKind != JsonValueKind.Null))
        {
            return CodexOutcome.Failed;
        }
        return eventType == "turn_aborted" ? null : CodexOutcome.Succeeded;
    }

    private static bool TryGetTimestamp(JsonElement record, JsonElement payload, out DateTimeOffset endedAt)
    {
        if (DateTimeOffset.TryParse(GetString(record, "timestamp"), CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal, out endedAt))
        {
            return true;
        }
        if (payload.TryGetProperty("completed_at", out var stamp) && stamp.ValueKind == JsonValueKind.Number
            && stamp.TryGetInt64(out var seconds) && seconds is > 0 and <= 253402300799)
        {
            endedAt = DateTimeOffset.FromUnixTimeSeconds(seconds);
            return true;
        }
        return false;
    }

    private static bool IsFileError(Exception error) => error is IOException or UnauthorizedAccessException;

    private static string? GetString(JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var property)
                                                && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;
}

internal enum CodexOutcome { Succeeded, Failed }

internal readonly record struct CodexCompletion(
    (string Thread, string Turn) Key, DateTimeOffset EndedAt, CodexOutcome Outcome);

internal sealed record CodexActivity(bool IsActive, IReadOnlyList<CodexCompletion> Completions)
{
    internal static CodexActivity Empty { get; } = new(false, []);
}
