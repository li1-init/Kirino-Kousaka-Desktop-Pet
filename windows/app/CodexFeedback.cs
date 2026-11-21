namespace KirinoDesktopPet;

internal sealed class CodexFeedback
{
    private readonly Dictionary<(string Thread, string Turn), DateTimeOffset> _seen = new();
    private readonly Queue<CodexOutcome> _pending = new();

    internal DateTimeOffset StartedAt { get; private set; }

    internal void Reset(DateTimeOffset now)
    {
        StartedAt = now;
        _pending.Clear();
        _seen.Clear();
    }

    internal void Add(CodexActivity activity, DateTimeOffset now)
    {
        var cutoff = now.AddMinutes(-10);
        foreach (var entry in _seen.Where(entry => entry.Value < cutoff).ToArray())
        {
            _seen.Remove(entry.Key);
        }
        foreach (var completion in activity.Completions.OrderBy(completion => completion.EndedAt))
        {
            if (completion.EndedAt >= StartedAt && completion.EndedAt >= cutoff
                && _seen.TryAdd(completion.Key, completion.EndedAt))
            {
                _pending.Enqueue(completion.Outcome);
            }
        }
    }

    internal bool TryTake(out CodexOutcome outcome) => _pending.TryDequeue(out outcome);
}
