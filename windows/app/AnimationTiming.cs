namespace KirinoDesktopPet;

internal static class AnimationTiming
{
    internal static int FrameAt(int[] endTimes, TimeSpan elapsed, bool loop)
    {
        var milliseconds = (long)elapsed.TotalMilliseconds;
        if (loop)
        {
            milliseconds %= endTimes[^1];
        }
        else if (milliseconds >= endTimes[^1])
        {
            return endTimes.Length - 1;
        }

        var index = Array.BinarySearch(endTimes, (int)milliseconds);
        return index < 0 ? ~index : index + 1;
    }
}

internal enum SessionMotion { Typing, Thinking, Glance }

internal sealed class SessionPlayback
{
    private long _lastThinkingSlot;
    private long _lastGlanceSlot;
    private TimeSpan _lastUpdate;

    internal SessionMotion Motion { get; private set; }
    internal double ClipMilliseconds { get; private set; }

    internal void Reset(SessionMotion motion = SessionMotion.Typing)
    {
        Motion = motion;
        ClipMilliseconds = 0;
        _lastThinkingSlot = 0;
        _lastGlanceSlot = 0;
        _lastUpdate = TimeSpan.Zero;
    }

    internal void Advance(
        TimeSpan elapsed,
        int speedPercent,
        int durationMilliseconds,
        bool followSession,
        TimeSpan thinkingInterval,
        TimeSpan glanceInterval)
    {
        ClipMilliseconds += (elapsed - _lastUpdate).TotalMilliseconds * speedPercent / 100;
        _lastUpdate = elapsed;

        var thinkingSlot = elapsed.Ticks / thinkingInterval.Ticks;
        var glanceSlot = elapsed.Ticks / glanceInterval.Ticks;
        var thinkingDue = followSession && thinkingSlot > _lastThinkingSlot;
        var glanceDue = followSession && glanceSlot > _lastGlanceSlot;
        _lastThinkingSlot = thinkingSlot;
        _lastGlanceSlot = glanceSlot;
        if (glanceDue)
        {
            Motion = SessionMotion.Glance;
            ClipMilliseconds = 0;
        }
        else if (thinkingDue)
        {
            Motion = SessionMotion.Thinking;
            ClipMilliseconds = 0;
        }
        else if (followSession && Motion != SessionMotion.Typing && ClipMilliseconds >= durationMilliseconds)
        {
            Motion = SessionMotion.Typing;
            ClipMilliseconds = 0;
        }
    }
}
