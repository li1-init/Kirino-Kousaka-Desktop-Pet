namespace KirinoDesktopPet;

internal static class AnimationTiming
{
    internal static readonly TimeSpan TypingInterval = TimeSpan.FromMinutes(2);

    internal static (bool Thinking, TimeSpan ClipTime) AutomaticClipAt(
        TimeSpan elapsed, TimeSpan thinkingDuration)
    {
        var position = TimeSpan.FromTicks(elapsed.Ticks % (TypingInterval + thinkingDuration).Ticks);
        return position < TypingInterval ? (false, position) : (true, position - TypingInterval);
    }

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
