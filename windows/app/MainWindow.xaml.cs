namespace KirinoDesktopPet;

using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

public partial class MainWindow : Window
{
    private const int CellWidth = 192;
    private const int CellHeight = 208;
    private const int AtlasColumns = 8;
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromMilliseconds(16) };
    private readonly DispatcherTimer _activityTimer = new() { Interval = TimeSpan.FromSeconds(2) };
    private readonly Stopwatch _animation = new();
    private readonly Dictionary<PetState, ImageSource[]> _sheetFrames = new();
    private MotionClip _typing = null!;
    private MotionClip _thinking = null!;
    private PetState _manualState;
    private bool _autoFollowCodex = true;
    private bool _codexSessionActive;
    private bool _checkingActivity;
    private Point _dragOffset;
    private MenuItem _autoFollowMenuItem = null!;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += (_, _) =>
        {
            _timer.Stop();
            _activityTimer.Stop();
        };
        _timer.Tick += (_, _) => ShowFrame();
        _activityTimer.Tick += (_, _) => RefreshCodexActivity();
        PetImage.LostMouseCapture += OnDragEnd;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var assets = Path.Combine(AppContext.BaseDirectory, "assets");
        try
        {
            var atlas = LoadAtlas(assets, "spritesheet");
            _sheetFrames.Add(PetState.Idle, ReadRow(atlas, 0, 6));
            _sheetFrames.Add(PetState.Waving, ReadRow(atlas, 3, 4));
            _sheetFrames.Add(PetState.HugGame, ReadRow(atlas, 4, 5));
            _sheetFrames.Add(PetState.Jumping, ReadRow(LoadAtlas(assets, "classic-jump"), 0, 5));
            _sheetFrames.Add(PetState.Failed, ReadRow(atlas, 5, 8));
            _sheetFrames.Add(PetState.Waiting, ReadRow(atlas, 6, 6));
            _sheetFrames.Add(PetState.Review, ReadRow(atlas, 8, 6));

            var durations = JsonSerializer.Deserialize<Dictionary<string, int[]>>(
                File.ReadAllText(Path.Combine(assets, "timings.json")));
            _typing = LoadClip(assets, "laptop-typing", durations);
            _thinking = LoadClip(assets, "laptop-thinking", durations);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException
                                      or JsonException or NotSupportedException
                                      or ArgumentException or FileFormatException
                                      or InvalidDataException or OverflowException)
        {
            MessageBox.Show(this, $"无法加载桌宠素材。请完整解压发布包后重试。\n{error.Message}",
                Title, MessageBoxButton.OK, MessageBoxImage.Error);
            Close();
            return;
        }

        var workArea = SystemParameters.WorkArea;
        Left = Math.Max(workArea.Left, workArea.Right - Width - 24);
        Top = Math.Max(workArea.Top, workArea.Bottom - Height - 24);
        BuildContextMenu();
        RestartAnimation();
        _timer.Start();
        _activityTimer.Start();
        RefreshCodexActivity();
    }

    private async void RefreshCodexActivity()
    {
        if (!_autoFollowCodex || _checkingActivity)
        {
            return;
        }

        _checkingActivity = true;
        try
        {
            var active = await Task.Run(CodexActivityMonitor.IsSessionActive);
            if (_timer.IsEnabled && _autoFollowCodex && active != _codexSessionActive)
            {
                _codexSessionActive = active;
                RestartAnimation();
            }
        }
        finally
        {
            _checkingActivity = false;
        }
    }

    private void RestartAnimation()
    {
        _animation.Restart();
        ShowFrame();
    }

    private void ShowFrame()
    {
        var elapsed = _animation.Elapsed;
        if (_autoFollowCodex && _codexSessionActive)
        {
            var (thinking, clipTime) = AnimationTiming.AutomaticClipAt(
                elapsed, TimeSpan.FromMilliseconds(_thinking.EndTimes[^1]));
            PetImage.Source = (thinking ? _thinking : _typing).FrameAt(clipTime, loop: !thinking);
        }
        else if (_manualState == PetState.Working)
        {
            PetImage.Source = _typing.FrameAt(elapsed);
        }
        else
        {
            var frames = _sheetFrames[_manualState];
            PetImage.Source = frames[(int)((long)elapsed.TotalMilliseconds / 100 % frames.Length)];
        }
    }

    private static BitmapSource LoadAtlas(string assets, string name)
    {
        using var stream = File.OpenRead(Path.Combine(assets, $"{name}.png"));
        var atlas = new PngBitmapDecoder(stream, BitmapCreateOptions.PreservePixelFormat,
            BitmapCacheOption.OnLoad).Frames[0];
        atlas.Freeze();
        return atlas;
    }

    private static ImageSource[] ReadRow(BitmapSource atlas, int row, int count) =>
        Enumerable.Range(0, count).Select(column => ReadCell(atlas, row, column)).ToArray();

    private static ImageSource ReadCell(BitmapSource atlas, int row, int column)
    {
        var frame = new CroppedBitmap(atlas,
            new Int32Rect(column * CellWidth, row * CellHeight, CellWidth, CellHeight));
        frame.Freeze();
        return frame;
    }

    private static MotionClip LoadClip(string assets, string name, Dictionary<string, int[]>? timings)
    {
        if (timings is null || !timings.TryGetValue(name, out var durations)
            || durations is not { Length: > 0 } || durations.Any(duration => duration <= 0))
        {
            throw new InvalidDataException($"Invalid frame timings: {name}");
        }
        var endTimes = new int[durations.Length];
        var atlas = LoadAtlas(assets, name);
        var frames = new ImageSource[durations.Length];
        var total = 0;
        for (var index = 0; index < durations.Length; index++)
        {
            total = checked(total + durations[index]);
            endTimes[index] = total;
            frames[index] = ReadCell(atlas, index / AtlasColumns, index % AtlasColumns);
        }
        return new MotionClip(frames, endTimes);
    }

    private void SetManualState(PetState state)
    {
        _autoFollowCodex = false;
        _codexSessionActive = false;
        _manualState = state;
        _autoFollowMenuItem.IsChecked = false;
        RestartAnimation();
    }

    private void ToggleAutoFollow()
    {
        if (_autoFollowCodex)
        {
            SetManualState(PetState.Idle);
            return;
        }
        _autoFollowCodex = true;
        _manualState = PetState.Idle;
        _autoFollowMenuItem.IsChecked = true;
        RestartAnimation();
        RefreshCodexActivity();
    }

    private void BuildContextMenu()
    {
        var menu = new ContextMenu();
        _autoFollowMenuItem = new MenuItem
        {
            Header = "自动跟随 Codex 会话", IsCheckable = true, IsChecked = _autoFollowCodex
        };
        _autoFollowMenuItem.Click += (_, _) => ToggleAutoFollow();
        menu.Items.Add(_autoFollowMenuItem);
        menu.Items.Add(new Separator());
        AddStateItem("待机", PetState.Idle);
        AddStateItem("工作 / 敲笔记本", PetState.Working);
        AddStateItem("等待 / 抱臂回望", PetState.Waiting);
        AddStateItem("审查 / 展示游戏盒", PetState.Review);
        AddStateItem("抱盒微笑", PetState.HugGame);
        AddStateItem("挥手", PetState.Waving);
        AddStateItem("跳跃", PetState.Jumping);
        AddStateItem("失败", PetState.Failed);
        menu.Items.Add(new Separator());
        var exit = new MenuItem { Header = "退出桐乃桌面宠物" };
        exit.Click += (_, _) => Close();
        menu.Items.Add(exit);
        PetImage.ContextMenu = menu;

        void AddStateItem(string label, PetState state)
        {
            var item = new MenuItem { Header = label };
            item.Click += (_, _) => SetManualState(state);
            menu.Items.Add(item);
        }
    }

    private void PetImage_OnMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            var working = _codexSessionActive || _manualState == PetState.Working;
            SetManualState(working ? PetState.Idle : PetState.Working);
            return;
        }

        _dragOffset = e.GetPosition(this);
        if (PetImage.CaptureMouse())
        {
            MouseMove += OnDrag;
            MouseLeftButtonUp += OnDragEnd;
        }
    }

    private void OnDrag(object sender, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed)
        {
            OnDragEnd(sender, e);
            return;
        }

        var delta = e.GetPosition(this) - _dragOffset;
        Left += delta.X;
        Top += delta.Y;
    }

    private void OnDragEnd(object? sender, MouseEventArgs e)
    {
        MouseMove -= OnDrag;
        MouseLeftButtonUp -= OnDragEnd;
        if (PetImage.IsMouseCaptured)
        {
            PetImage.ReleaseMouseCapture();
        }
    }

    private void PetImage_OnMouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        PetImage.ContextMenu.IsOpen = true;
        e.Handled = true;
    }

    private sealed record MotionClip(ImageSource[] Frames, int[] EndTimes)
    {
        public ImageSource FrameAt(TimeSpan elapsed, bool loop = true) =>
            Frames[AnimationTiming.FrameAt(EndTimes, elapsed, loop)];
    }

    private enum PetState { Idle, Working, Waiting, Review, HugGame, Failed, Waving, Jumping }
}
