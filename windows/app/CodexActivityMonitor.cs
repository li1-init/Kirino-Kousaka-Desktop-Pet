namespace KirinoDesktopPet;

using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

internal static class CodexActivityMonitor
{
    private static readonly TimeSpan RecentWriteWindow = TimeSpan.FromMinutes(10);
    private const int SessionTailBytes = 256 * 1024;

    public static bool IsSessionActive()
    {
        try
        {
            if (!HasRunningCodexProcess())
            {
                return false;
            }
            var home = Environment.GetEnvironmentVariable("CODEX_HOME");
            if (string.IsNullOrWhiteSpace(home))
            {
                home = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".codex");
            }
            return AnySessionActive(home, DateTime.UtcNow);
        }
        catch (Exception error) when (IsFileError(error) || error is Win32Exception
                                      or InvalidOperationException or ArgumentException)
        {
            return false;
        }
    }

    internal static bool AnySessionActive(string codexHome, DateTime now)
    {
        var cutoff = now - RecentWriteWindow;
        var locks = ReadBusyLocks(Path.Combine(codexHome, "thread-writer-locks"));
        var latest = new Dictionary<Guid, (string Path, DateTime LastWriteUtc)>();
        var sessionRoot = Path.Combine(codexHome, "sessions");
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
                else if (ReadLatestActivity(file) == true)
                {
                    return true;
                }
            }
            catch (Exception error) when (IsFileError(error))
            {
                // Files can be rotated or become inaccessible during a scan.
            }
        }

        foreach (var (id, session) in latest)
        {
            var active = ReadLatestActivity(session.Path);
            if (active == true || (active is null && locks.GetValueOrDefault(id) >= cutoff))
            {
                return true;
            }
        }
        return locks.Any(entry => entry.Value >= cutoff && !latest.ContainsKey(entry.Key));
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

    private static bool? ReadLatestActivity(string file)
    {
        bool? active = null;
        bool? legacySignal = null;
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
                            switch (GetString(payload, "type"))
                            {
                                case "task_started" or "turn_started":
                                    active = true;
                                    break;
                                case "task_complete" or "turn_aborted" or "turn_completed" or "turn_complete":
                                    active = false;
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

    private static bool IsFileError(Exception error) => error is IOException or UnauthorizedAccessException;

    private static string? GetString(JsonElement element, string name) =>
        element.ValueKind == JsonValueKind.Object && element.TryGetProperty(name, out var property)
                                                && property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;
}
