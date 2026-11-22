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

        var playback = new SessionPlayback();
        playback.Advance(TimeSpan.FromSeconds(29), 150, 3100, true,
            TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
        Require(playback.Motion == SessionMotion.Typing, "Typing starts immediately");
        foreach (var seconds in new[] { 30, 60, 90, 120, 150, 180, 210, 240 })
        {
            var trigger = TimeSpan.FromSeconds(seconds);
            var expected = seconds % 120 == 0 ? SessionMotion.Glance : SessionMotion.Thinking;
            playback.Advance(trigger, 150, 3100, true,
                TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
            Require(playback.Motion == expected && playback.ClipMilliseconds == 0,
                "Glance has priority on each two-minute boundary, otherwise think every thirty seconds");
            playback.Advance(trigger + TimeSpan.FromSeconds(3), 50, 3100, true,
                TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
            Require(playback.Motion == expected && playback.ClipMilliseconds == 1500,
                "The one-shot uses its own playback speed");
            playback.Advance(trigger + TimeSpan.FromSeconds(4), 100, 3100, true,
                TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
            Require(playback.ClipMilliseconds == 2500, "Changing speed preserves playback progress");
            playback.Advance(trigger + TimeSpan.FromSeconds(5), 100, 3100, true,
                TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
            Require(playback.Motion == SessionMotion.Typing && playback.ClipMilliseconds == 0,
                "Playback returns to typing after each one-shot");
        }
        playback.Reset();
        playback.Advance(TimeSpan.FromSeconds(120), 100, 3100, false,
            TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(120));
        Require(playback.Motion == SessionMotion.Typing, "Manual typing never switches to another motion");
        playback.Reset();
        playback.Advance(TimeSpan.FromSeconds(60), 100, 3100, true,
            TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(60));
        Require(playback.Motion == SessionMotion.Glance, "The glance interval is configurable");
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
            Require(settings.Save(137) && new PetSizeSettings(path).Load() == 137, "Intermediate sizes persist");
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
        var window = new MainWindow(settings, _ => true);
        window.Show();
        var dispatcher = window.Dispatcher;
        dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        Require(window.Topmost && window.AllowsTransparency && !window.ShowInTaskbar,
            "Window appearance matches the README");
        var image = (Image)window.FindName("PetImage");
        var deadline = System.Diagnostics.Stopwatch.StartNew();
        while (image.Source is not BitmapSource { PixelWidth: 224, PixelHeight: 232 }
            && deadline.Elapsed < TimeSpan.FromSeconds(3))
        {
            Thread.Sleep(10);
            dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        }
        Require(image.Source is BitmapSource { PixelWidth: 224, PixelHeight: 232 },
            "Active following displays the cushion typing clip");
        var items = image.ContextMenu!.Items.OfType<MenuItem>().ToArray();
        Require(items.Length == 5 && Equals(items[0].Header, "自动跟随 Codex 会话")
            && Equals(items[1].Header, "敲笔记本")
            && Equals(items[2].Header, "看屏幕思考")
            && Equals(items[3].Header, "回眸脸红嘟嘴")
            && Equals(items[4].Header, "退出"), "The context menu has the requested action levels");
        Require(items[0].IsCheckable && items[0].IsChecked
            && items.Skip(1).Take(3).All(item => item.IsCheckable && !item.IsChecked),
            "Automatic following starts as the only checked mode");
        var typingSliders = ActionSliders(items[1]);
        var thinkingSliders = ActionSliders(items[2]);
        var glanceSliders = ActionSliders(items[3]);
        Require(typingSliders.Length == 2 && thinkingSliders.Length == 2 && glanceSliders.Length == 3,
            "Each action exposes size and speed, with a glance interval");
        Require(typingSliders.All(slider => slider.Value == 100)
            && thinkingSliders.All(slider => slider.Value == 100)
            && glanceSliders[0].Value == 100 && glanceSliders[1].Value == 100
            && glanceSliders[2].Value == 120, "Action settings have the documented defaults");
        Require(typingSliders[1].Minimum == 50 && typingSliders[1].Maximum == 150
            && glanceSliders[2].Minimum == 30 && glanceSliders[2].Maximum == 600,
            "Action speed and glance interval ranges are available");
        thinkingSliders[1].Value = 67;
        glanceSliders[2].Value = 180;
        Require(typingSliders[1].Value == 100 && glanceSliders[1].Value == 100,
            "Action speeds and intervals are independent");
        typingSliders[0].Value = 137;
        Require(thinkingSliders[0].Value == 137 && glanceSliders[0].Value == 137,
            "All actions share one size slider");
        window.UpdateLayout();
        var scale = Math.Min(1.37, Math.Min(PetWindowBounds.WorkArea(window).Width / 192,
            PetWindowBounds.WorkArea(window).Height / 208));
        Require(Math.Abs(window.Width - 192 * scale) < 1 && Math.Abs(window.Height - 208 * scale) < 1,
            $"Sliding resizes to intermediate percentages: {window.Width} × {window.Height}, scale {scale}");
        var autoFollow = items.First();
        Require(autoFollow.IsChecked, "Automatic following starts enabled");
        autoFollow.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(!autoFollow.IsChecked, "The menu can disable automatic following");
        Require(image.Source is BitmapSource { PixelWidth: 344, PixelHeight: 232 },
            "Disabling following returns to the phone idle animation");
        items[3].RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(items[3].IsChecked && !autoFollow.IsChecked
            && !items[1].IsChecked && !items[2].IsChecked,
            "Selecting a fixed action checks only that action");
        Require(image.Source is BitmapSource { PixelWidth: 224, PixelHeight: 232 },
            "A fixed action keeps playing its selected clip");
        autoFollow.RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(autoFollow.IsChecked && items.Skip(1).Take(3).All(item => !item.IsChecked),
            "Automatic following clears the fixed-action checks");
        items.Last().RaiseEvent(new RoutedEventArgs(MenuItem.ClickEvent));
        Require(!window.IsVisible, "The exit action closes the window");
        var reopened = new MainWindow(settings, _ => false);
        reopened.Show();
        dispatcher.Invoke(() => { }, DispatcherPriority.ApplicationIdle);
        Require(settings.Load() == 137 && Math.Abs(reopened.Width - window.Width) < 1
            && Math.Abs(reopened.Height - window.Height) < 1,
            "The saved size is restored when reopening");
        reopened.Close();
        application.Shutdown();
        root.Delete(recursive: true);

        static Slider[] ActionSliders(MenuItem item) =>
            item.Items.OfType<MenuItem>()
                .Select(child => ((StackPanel)child.Header).Children.OfType<Slider>().Single())
                .ToArray();
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
