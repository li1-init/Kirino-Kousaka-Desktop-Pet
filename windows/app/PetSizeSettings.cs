namespace KirinoDesktopPet;

using System.IO;
using System.Text.Json;

internal sealed class PetSizeSettings(string path)
{
    internal const int Default = 100;
    internal static IReadOnlyList<int> Sizes { get; } = Array.AsReadOnly(new[] { 50, 75, 100, 125, 150, 175, 200 });

    internal static PetSizeSettings ForCurrentUser() => new(Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "KirinoDesktopPet", "settings.json"));

    internal int Load()
    {
        try
        {
            using var settings = JsonDocument.Parse(File.ReadAllText(path));
            var root = settings.RootElement;
            if (root.ValueKind == JsonValueKind.Object
                && root.TryGetProperty("sizePercent", out var size)
                && size.ValueKind == JsonValueKind.Number
                && size.TryGetInt32(out var percent)
                && Sizes.Contains(percent))
            {
                return percent;
            }
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or JsonException)
        {
            // An unavailable or invalid preference falls back to the original size.
        }
        return Default;
    }

    internal bool Save(int percent)
    {
        if (!Sizes.Contains(percent))
        {
            return false;
        }

        var staged = $"{path}.{Guid.NewGuid():N}.tmp";
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(staged, JsonSerializer.Serialize(new { sizePercent = percent }));
            File.Move(staged, path, overwrite: true);
            return true;
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            try
            {
                File.Delete(staged);
            }
            catch (Exception cleanupError) when (cleanupError is IOException or UnauthorizedAccessException)
            {
                // Failure to remove a temporary file cannot affect the current preference.
            }
            return false;
        }
    }
}
