namespace KirinoDesktopPet;

using System.Diagnostics;
using System.IO;
using System.Text.Json;

internal static class CodexActivityMonitor
{
    // A model turn can spend several minutes thinking without appending a new
    // line to the rollout file. Keep the log signal as a fallback, but give it
    // enough room to cover those quiet periods.
    private static readonly TimeSpan RecentWriteWindow = TimeSpan.FromMinutes(10);
    private const int SessionTailBytes = 256 * 1024;

    public static bool IsSessionActive()
    {
        if (!HasRunningCodexProcess())
        {
            return false;
        }

        var codexHome = Environment.GetEnvironmentVariable("CODEX_HOME");
        if (string.IsNullOrWhiteSpace(codexHome))
        {
            codexHome = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                ".codex");
        }

        var sessionRoot = Path.Combine(codexHome, "sessions");
        var lockRoot = Path.Combine(codexHome, "thread-writer-locks");
        var cutoff = DateTime.UtcNow - RecentWriteWindow;
        var busyThreadIds = GetBusyThreadIds(lockRoot);
        if (!Directory.Exists(sessionRoot))
        {
            return busyThreadIds.Any(id => IsRecentLock(lockRoot, id, cutoff));
        }

        var latestByThread = new Dictionary<string, (DateTime LastWriteUtc, bool? IsActive)>(
            StringComparer.OrdinalIgnoreCase);
        try
        {
            foreach (var file in Directory.EnumerateFiles(
                         sessionRoot,
                         "*.jsonl",
                         SearchOption.AllDirectories))
            {
                try
                {
                    var lastWriteUtc = File.GetLastWriteTimeUtc(file);
                    var threadId = busyThreadIds
                        .FirstOrDefault(id => Path.GetFileName(file)
                            .Contains(id, StringComparison.OrdinalIgnoreCase));
                    var isActive = lastWriteUtc >= cutoff
                        ? ReadLatestActivity(file)
                        : null;
                    if (threadId is not null &&
                        (!latestByThread.TryGetValue(threadId, out var previous) ||
                         lastWriteUtc > previous.LastWriteUtc))
                    {
                        latestByThread[threadId] = (lastWriteUtc, ReadLatestActivity(file));
                    }
                    else if (lastWriteUtc >= cutoff && isActive == true)
                    {
                        return true;
                    }
                }
                catch (IOException)
                {
                    // Codex can rotate or lock a session file while it is being written.
                }
                catch (UnauthorizedAccessException)
                {
                    // A single inaccessible session file should not stop monitoring.
                }
            }
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }

        foreach (var threadId in busyThreadIds)
        {
            if (latestByThread.TryGetValue(threadId, out var snapshot))
            {
                // The lock protects a long-running turn. The log state tells
                // us whether the latest turn actually ended.
                if (snapshot.IsActive == true)
                {
                    return true;
                }
            }
            else if (IsRecentLock(lockRoot, threadId, cutoff))
            {
                // A newly created thread can acquire its lock before its
                // first rollout file is visible.
                return true;
            }
        }

        return false;
    }

    private static bool HasRunningCodexProcess()
    {
        try
        {
            return Process.GetProcessesByName("codex")
                .Any(process => !process.HasExited);
        }
        catch (InvalidOperationException)
        {
            return false;
        }
        catch (System.ComponentModel.Win32Exception)
        {
            return false;
        }
    }

    private static HashSet<string> GetBusyThreadIds(string lockRoot)
    {
        var busyThreadIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (!Directory.Exists(lockRoot))
        {
            return busyThreadIds;
        }

        try
        {
            foreach (var lockFile in Directory.EnumerateFiles(lockRoot, "*.lock"))
            {
                if (Path.GetFileName(lockFile).Equals(
                        ".coordination.lock",
                        StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                try
                {
                    // An exclusive open succeeds when the lock is not held.
                    // Sharing None makes this check independent of the lock
                    // file's zero-byte contents and last-write timestamp.
                    using var stream = new FileStream(
                        lockFile,
                        FileMode.Open,
                        FileAccess.ReadWrite,
                        FileShare.None);
                }
                catch (IOException)
                {
                    busyThreadIds.Add(Path.GetFileNameWithoutExtension(lockFile));
                }
                catch (UnauthorizedAccessException)
                {
                    busyThreadIds.Add(Path.GetFileNameWithoutExtension(lockFile));
                }
            }
        }
        catch (IOException)
        {
            return busyThreadIds;
        }
        catch (UnauthorizedAccessException)
        {
            return busyThreadIds;
        }

        return busyThreadIds;
    }

    private static bool IsRecentLock(string lockRoot, string threadId, DateTime cutoff)
    {
        var lockFile = Path.Combine(lockRoot, $"{threadId}.lock");
        try
        {
            return File.Exists(lockFile) &&
                   File.GetLastWriteTimeUtc(lockFile) >= cutoff;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static bool? ReadLatestActivity(string file)
    {
        bool? active = null;
        try
        {
            using var stream = new FileStream(
                file,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete);
            stream.Seek(Math.Max(0, stream.Length - SessionTailBytes), SeekOrigin.Begin);
            using var reader = new StreamReader(stream);
            while (reader.ReadLine() is { } line)
            {
                try
                {
                    using var document = JsonDocument.Parse(line);
                    var root = document.RootElement;
                    var recordType = GetString(root, "type");
                    var payloadType = root.TryGetProperty("payload", out var payload)
                        ? GetString(payload, "type")
                        : null;

                    if (payloadType is "task_complete" or
                        "turn_aborted" or
                        "turn_completed" or
                        "turn_complete")
                    {
                        active = false;
                    }
                    else if (recordType is "response_item" ||
                             payloadType is "item_started" or
                             "item_completed" or
                             "turn_started")
                    {
                        active = true;
                    }
                }
                catch (JsonException)
                {
                    // A writer can be observed between two JSONL writes.
                }
            }
        }
        catch (IOException)
        {
            return null;
        }
        catch (UnauthorizedAccessException)
        {
            return null;
        }

        return active;
    }

    private static string? GetString(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
               property.ValueKind == JsonValueKind.String
            ? property.GetString()
            : null;
    }
}
