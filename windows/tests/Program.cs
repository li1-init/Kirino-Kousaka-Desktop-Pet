using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using KirinoDesktopPet;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        VerifyAnimationTiming();
        VerifyActivityMonitor();
        VerifyCodexFeedback();
        VerifySizing();
        if (args.Contains("--ui"))
        {
            VerifyWindow();
        }
        Console.WriteLine("Standalone verification passed.");
    }

    private static void VerifyAnimationTiming()
    {
        var frames = new[] { 330, 346, 363 };
        Require(AnimationTiming.FrameAt(frames, TimeSpan.Zero, true) == 0, "First frame is shown");
        Require(AnimationTiming.FrameAt(frames, TimeSpan.FromMilliseconds(330), true) == 1,
            "Short frames follow the authored timing");
        Require(AnimationTiming.FrameAt(frames, TimeSpan.FromMilliseconds(363), true) == 0, "Typing loops");
        Require(AnimationTiming.FrameAt(frames, TimeSpan.FromMilliseconds(363), false) == 2,
            "Thinking ends on its last frame");

        var duration = TimeSpan.FromSeconds(5);
        Require(AnimationTiming.AutomaticClipAt(TimeSpan.FromMilliseconds(119999), duration).Thinking == false,
            "Typing runs for two minutes");
        Require(AnimationTiming.AutomaticClipAt(TimeSpan.FromSeconds(120), duration) == (true, TimeSpan.Zero),
            "Thinking starts from its first frame");
        Require(AnimationTiming.AutomaticClipAt(TimeSpan.FromMilliseconds(124999), duration).Thinking,
            "Thinking runs for its full authored duration");
        Require(AnimationTiming.AutomaticClipAt(TimeSpan.FromSeconds(125), duration) == (false, TimeSpan.Zero),
            "The cycle returns to typing");
        Require(AnimationTiming.AutomaticClipAt(TimeSpan.FromSeconds(245), duration).Thinking,
            "The cycle repeats");
    }

    private static void VerifyActivityMonitor()
    {
        var root = Directory.CreateTempSubdirectory("kirino-qa-");
        try
        {
            var sessions = root.CreateSubdirectory("sessions");
            var locks = root.CreateSubdirectory("thread-writer-locks");
            var id = Guid.NewGuid();
            var now = DateTime.UtcNow;
            var first = Path.Combine(sessions.FullName, $"rollout-a-{id:D}.jsonl");
            var newest = Path.Combine(sessions.FullName, $"rollout-b-{id:D}.jsonl");
            var lockPath = Path.Combine(locks.FullName, $"{id:D}.lock");
            const string started = """{"type":"event_msg","payload":{"type":"task_started"}}""";
            const string finished = """{"type":"event_msg","payload":{"type":"task_complete"}}""";
            const string aborted = """{"type":"event_msg","payload":{"type":"turn_aborted"}}""";
            const string response = """{"type":"response_item","payload":[]}""";

            WriteLog(first, now.AddMinutes(-2), started, "[]", """{"type":"event_msg","payload":null}""", "{");
            Require(Active(), "Start is recognized and malformed or incomplete lines are ignored");
            WriteLog(newest, now.AddMinutes(-1), finished, response);
            Require(!Active(), "The newest rollout and its terminal event take precedence");
            WriteLog(newest, now.AddMinutes(-1), started, aborted);
            Require(!Active(), "An interrupted turn returns to idle");
            WriteLog(newest, now.AddHours(-1), started);
            File.SetLastWriteTimeUtc(first, now.AddHours(-2));
            File.WriteAllText(lockPath, "");
            Require(!Active(), "Stale logs and released locks are ignored");
            using (File.Open(lockPath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                Require(Active(), "A held lock keeps a quiet turn active");
                WriteLog(newest, now.AddHours(-1), finished);
                Require(!Active(), "A held lock does not override a terminal event");
            }

            bool Active() => CodexActivityMonitor.ReadActivity(root.FullName, now, now).IsActive;
        }
        finally
        {
            root.Delete(recursive: true);
        }
    }

    private static void VerifyCodexFeedback()
    {
        var root = Directory.CreateTempSubdirectory("kirino-feedback-");
        try
        {
            var sessions = root.CreateSubdirectory("sessions");
            var now = DateTimeOffset.UtcNow;
            var first = Path.Combine(sessions.FullName, $"rollout-a-{Guid.NewGuid():D}.jsonl");
            var second = Path.Combine(sessions.FullName, $"rollout-b-{Guid.NewGuid():D}.jsonl");
            var feedback = new CodexFeedback();
            feedback.Reset(now.AddSeconds(-5));
            WriteLog(first, now.UtcDateTime,
                Event("task_complete", "before-startup", now.AddMinutes(-1)),
                Event("task_started", "try-1", now.AddSeconds(-4)),
                Event("task_complete", "try-1", now.AddSeconds(-3)),
                Event("task_started", "try-2", now.AddSeconds(-2)),
                Event("task_complete", "try-2", now.AddSeconds(-1), new { message = "test failure" }),
                Event("task_started", "try-3", now),
                Event("task_complete", "try-2", now, new { message = "duplicate" }));
            WriteLog(second, now.UtcDateTime,
                Event("task_started", "other-1", now.AddSeconds(-3)),
                Event("turn_aborted", "other-1", now.AddSeconds(-2)));

            var activity = CodexActivityMonitor.ReadActivity(root.FullName, now.UtcDateTime, feedback.StartedAt);
            Require(activity.IsActive, "A late completion must not stop a newer active turn");
            feedback.Add(activity, now);
            feedback.Add(activity, now);
            Require(feedback.TryTake(out var success) && success == CodexOutcome.Succeeded,
                "A successful completion is delivered once");
            Require(feedback.TryTake(out var failure) && failure == CodexOutcome.Failed,
                "A terminal error is delivered once");
            Require(!feedback.TryTake(out _), "Startup history, cancellations and duplicate polls are silent");
        }
        finally
        {
            root.Delete(recursive: true);
        }
    }

    private static string Event(string type, string turnId, DateTimeOffset timestamp, object? error = null) =>
        System.Text.Json.JsonSerializer.Serialize(new
        {
            type = "event_msg", timestamp, payload = new { type, turn_id = turnId, error }
        });

    private static void VerifySizing()
    {
        var root = Directory.CreateTempSubdirectory("kirino-size-");
        try
        {
            var path = Path.Combine(root.FullName, "config", "settings.json");
            var settings = new PetSizeSettings(path);
            Require(settings.Load() == 100, "A new installation uses 100%");
            Require(!settings.Save(500) && !File.Exists(path), "Invalid sizes are not saved");
            Require(settings.Save(150) && new PetSizeSettings(path).Load() == 150, "Size persists across instances");
            File.WriteAllText(path, """{"sizePercent":0}""");
            Require(settings.Load() == 100, "An invalid saved size falls back to 100%");
            File.WriteAllText(path, "{");
            Require(settings.Load() == 100, "Corrupted settings fall back to 100%");
        }
        finally
        {
            root.Delete(recursive: true);
        }

        var baseSize = new Size(192, 208);
        var work = new Rect(-1280, 0, 1280, 700);
        var enlarged = PetWindowBounds.Resize(new Rect(-210, 480, 192, 208), work, baseSize, 200);
        Require(work.Contains(enlarged) && enlarged.Size == new Size(384, 416), "Growth fits the current monitor");
        var reduced = PetWindowBounds.Resize(enlarged, work, baseSize, 50);
        Require(work.Contains(reduced) && reduced.Bottom == enlarged.Bottom, "Shrinking keeps the ground position");
        work = new Rect(0, 0, 320, 208);
        var limited = PetWindowBounds.Resize(reduced, work, baseSize, 200);
        Require(work.Contains(limited) && limited.Size == baseSize, "Small work areas preserve the aspect ratio");
    }

    private static void VerifyWindow()
    {
        var application = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        var root = Directory.CreateTempSubdirectory("kirino-window-");
        var settings = new PetSizeSettings(Path.Combine(root.FullName, "settings.json"));
        var window = new MainWindow(settings);
        window.Show();
        var dispatcher = window.Dispatcher;
        dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        Require(window.Topmost && window.AllowsTransparency && !window.ShowInTaskbar,
            "Window appearance matches the README");
        var image = (Image)window.FindName("PetImage");
        Require(image.Source is BitmapSource { PixelWidth: 192, PixelHeight: 208 }, "A frame is displayed");
        var items = image.ContextMenu!.Items.OfType<MenuItem>().ToArray();
        var size = items.Single(item => Equals(item.Header, "宠物大小")).Items.OfType<MenuItem>().ToArray();
        Require(size.Length == 7 && size[2].IsChecked, "The size menu reflects the default");
        size[4].RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        window.UpdateLayout();
        Require(window.Width == 288 && window.Height == 312
            && image.ActualWidth == 288 && image.ActualHeight == 312, "The image and window resize together");
        Require(size.Count(item => item.IsChecked) == 1 && size[4].IsChecked, "Only the selected size is checked");
        var autoFollow = items.First();
        Require(autoFollow.IsChecked, "Automatic following starts enabled");
        autoFollow.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(!autoFollow.IsChecked, "The menu can disable automatic following");
        autoFollow.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(autoFollow.IsChecked, "The menu can reenable automatic following");
        foreach (var item in items.Skip(1).SkipLast(1).Where(item => !item.HasItems))
        {
            var previous = image.Source;
            item.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
            Require(!autoFollow.IsChecked && image.Source is BitmapSource, $"Manual action loads: {item.Header}");
            if (!Equals(item.Header, "待机"))
            {
                Require(!ReferenceEquals(previous, image.Source), $"Manual action changes frames: {item.Header}");
            }
        }
        items.Last().RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(!window.IsVisible, "The exit action closes the window");
        var reopened = new MainWindow(settings);
        reopened.Show();
        dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        Require(reopened.Width == 288 && reopened.Height == 312, "The saved size is restored when reopening");
        reopened.Close();
        application.Shutdown();
        root.Delete(recursive: true);
    }

    private static void WriteLog(string path, DateTime writeTime, params string[] lines)
    {
        File.WriteAllLines(path, lines);
        File.SetLastWriteTimeUtc(path, writeTime);
    }

    private static void Require(bool condition, string description)
    {
        if (!condition)
        {
            throw new InvalidOperationException(description);
        }
    }
}
