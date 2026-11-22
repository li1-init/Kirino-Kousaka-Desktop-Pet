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
    private const int SessionCellWidth = 224;
    private const int SessionCellHeight = 232;
    private const int AtlasColumns = 8;
    private readonly DispatcherTimer _timer = new() { Interval = TimeSpan.FromMilliseconds(16) };
    private readonly DispatcherTimer _activityTimer = new() { Interval = TimeSpan.FromSeconds(2) };
    private readonly Stopwatch _animation = new();
    private readonly SessionPlayback _playback = new();
    private readonly int[] _speeds = [100, 100, 100];
    private readonly MotionClip[] _sessionMotions = new MotionClip[3];
    private readonly List<Slider> _sizeControls = [];
    private readonly PetSizeSettings _sizeSettings;
    private readonly Func<DateTimeOffset, bool> _readActivity;
    private int _sizePercent;
    private int _savedSizePercent;
    private int _glanceIntervalSeconds = 120;
    private MotionClip _idleMotion = null!;
    private SessionMotion? _fixedMotion;
    private bool _autoFollowEnabled = true;
    private bool _codexSessionActive;
    private bool _checkingActivity;
    private DateTimeOffset _activitySince;
    private Point _dragOffset;
    private MenuItem _autoFollowMenuItem = null!;
    private readonly Dictionary<SessionMotion, MenuItem> _actionMenuItems = new();

    public MainWindow() : this(PetSizeSettings.ForCurrentUser())
    {
    }

    internal MainWindow(PetSizeSettings sizeSettings, Func<DateTimeOffset, bool>? readActivity = null)
    {
        _sizeSettings = sizeSettings;
        _readActivity = readActivity ?? (since => CodexActivityMonitor.ReadActivity(since).IsActive);
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += (_, _) =>
        {
            _timer.Stop();
            _activityTimer.Stop();
            SaveSize();
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
            var durations = JsonSerializer.Deserialize<Dictionary<string, int[]>>(
                File.ReadAllText(Path.Combine(assets, "timings.json")));
            _idleMotion = LoadClip(assets, "phone-idle", durations, 344, 232);
            _sessionMotions[(int)SessionMotion.Typing] = LoadClip(assets, "cushion-typing", durations);
            _sessionMotions[(int)SessionMotion.Thinking] = LoadClip(assets, "cushion-thinking", durations);
            _sessionMotions[(int)SessionMotion.Glance] = LoadClip(assets, "cushion-glance", durations);
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
        _sizePercent = _savedSizePercent = _sizeSettings.Load();
        ApplySize(_sizePercent, workArea);
        BuildContextMenu();
        _activitySince = DateTimeOffset.UtcNow;
        RestartAnimation();
        _timer.Start();
        _activityTimer.Start();
        RefreshCodexActivity();
    }

    private void ApplySize(int percent, Rect workArea)
    {
        var window = new Rect(Left, Top, Width, Height);
        var resized = PetWindowBounds.Resize(window, workArea, new Size(CellWidth, CellHeight), percent);
        Width = resized.Width;
        Height = resized.Height;
        Left = resized.Left;
        Top = resized.Top;
    }

    private async void RefreshCodexActivity()
    {
        if (!_autoFollowEnabled || _fixedMotion is not null || _checkingActivity)
        {
            return;
        }

        _checkingActivity = true;
        var since = _activitySince;
        try
        {
            var isActive = await Task.Run(() => _readActivity(since)).ConfigureAwait(false);
            await Dispatcher.InvokeAsync(() =>
            {
                _checkingActivity = false;
                if (!_timer.IsEnabled || !_autoFollowEnabled || _fixedMotion is not null
                    || since != _activitySince)
                {
                    return;
                }
                if (isActive != _codexSessionActive)
                {
                    _codexSessionActive = isActive;
                    RestartAnimation();
                }
            }).Task.ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (Dispatcher.HasShutdownStarted)
        {
            // The window closed while the background scan was finishing.
        }
    }

    private void RestartAnimation()
    {
        _playback.Reset(_fixedMotion ?? SessionMotion.Typing);
        _animation.Restart();
        ShowFrame();
    }

    private void ShowFrame()
    {
        var following = _autoFollowEnabled && _fixedMotion is null && _codexSessionActive;
        if (!following && _fixedMotion is null)
        {
            PetImage.Source = _idleMotion.FrameAt(_animation.Elapsed, loop: true);
            return;
        }

        var current = (int)_playback.Motion;
        _playback.Advance(
            _animation.Elapsed,
            _speeds[current],
            _sessionMotions[current].EndTimes[^1],
            following,
            TimeSpan.FromSeconds(30),
            TimeSpan.FromSeconds(_glanceIntervalSeconds));
        var motion = _playback.Motion;
        PetImage.Source = _sessionMotions[(int)motion].FrameAt(
            TimeSpan.FromMilliseconds(_playback.ClipMilliseconds), loop: !following || motion == SessionMotion.Typing);
    }

    private static BitmapSource LoadAtlas(string assets, string name)
    {
        using var stream = File.OpenRead(Path.Combine(assets, $"{name}.png"));
        var atlas = new PngBitmapDecoder(stream, BitmapCreateOptions.PreservePixelFormat,
            BitmapCacheOption.OnLoad).Frames[0];
        atlas.Freeze();
        return atlas;
    }

    private static ImageSource ReadCell(BitmapSource atlas, int row, int column, int width, int height)
    {
        var frame = new CroppedBitmap(atlas,
            new Int32Rect(column * width, row * height, width, height));
        frame.Freeze();
        return frame;
    }

    private static MotionClip LoadClip(
        string assets,
        string name,
        Dictionary<string, int[]>? timings,
        int cellWidth = SessionCellWidth,
        int cellHeight = SessionCellHeight)
    {
        if (timings is null || !timings.TryGetValue(name, out var durations)
            || durations is not { Length: > 0 } || durations.Any(duration => duration <= 0))
        {
            throw new InvalidDataException($"Invalid frame timings: {name}");
        }
        var atlas = LoadAtlas(assets, name);
        var frames = new ImageSource[durations.Length];
        for (var index = 0; index < durations.Length; index++)
        {
            frames[index] = ReadCell(atlas, index / AtlasColumns, index % AtlasColumns,
                cellWidth, cellHeight);
        }
        return new MotionClip(frames, EndTimes(durations));
    }

    private static int[] EndTimes(int[] durations)
    {
        var total = 0;
        return durations.Select(duration => total = checked(total + duration)).ToArray();
    }

    private void BuildContextMenu()
    {
        _sizeControls.Clear();
        var menu = new ContextMenu();
        _autoFollowMenuItem = new MenuItem
        {
            Header = "自动跟随 Codex 会话", IsCheckable = true, IsChecked = _autoFollowEnabled
        };
        _autoFollowMenuItem.Click += (_, _) => ToggleAutoFollow();
        menu.Items.Add(_autoFollowMenuItem);
        AddActionMenu("敲笔记本", SessionMotion.Typing);
        AddActionMenu("看屏幕思考", SessionMotion.Thinking);
        AddActionMenu("回眸脸红嘟嘴", SessionMotion.Glance);
        menu.Closed += (_, _) => SaveSize();
        var exit = new MenuItem { Header = "退出" };
        exit.Click += (_, _) => Close();
        menu.Items.Add(exit);
        PetImage.ContextMenu = menu;
        ContextMenu = menu;

        void AddActionMenu(string label, SessionMotion motion)
        {
            var action = new MenuItem
            {
                Header = label,
                IsCheckable = true,
                IsChecked = _fixedMotion == motion,
                StaysOpenOnClick = true,
                ToolTip = "展开后拖动滑块调整大小和速度"
            };
            _actionMenuItems[motion] = action;
            action.Click += (_, e) =>
            {
                if (ReferenceEquals(e.OriginalSource, action))
                {
                    SelectMode(motion);
                    Dispatcher.BeginInvoke(
                        DispatcherPriority.Input,
                        new Action(() => action.IsSubmenuOpen = true));
                }
            };
            action.Items.Add(SliderMenuItem("大小", PetSizeSettings.Minimum, PetSizeSettings.Maximum,
                _sizePercent, SetGlobalSize));
            action.Items.Add(SliderMenuItem("速度", 50, 150, _speeds[(int)motion],
                percent => _speeds[(int)motion] = percent));
            if (motion == SessionMotion.Glance)
            {
                action.Items.Add(SliderMenuItem("触发间隔", 30, 600, _glanceIntervalSeconds,
                    percent => _glanceIntervalSeconds = percent));
            }
            menu.Items.Add(action);
        }
    }

    private MenuItem SliderMenuItem(string label, int minimum, int maximum, int value, Action<int> apply)
    {
        var suffix = label == "触发间隔" ? " 秒" : "%";
        var caption = new TextBlock
        {
            Text = $"{label} {value}{suffix}",
            Width = 104,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(0, 0, 8, 0)
        };
        var slider = new Slider
        {
            Minimum = minimum, Maximum = maximum, Value = value,
            TickFrequency = 1, IsSnapToTickEnabled = true, IsMoveToPointEnabled = true,
            Width = 144, VerticalAlignment = VerticalAlignment.Center, ToolTip = label
        };
        System.Windows.Automation.AutomationProperties.SetName(slider, label);
        slider.ValueChanged += (_, e) =>
        {
            var setting = (int)e.NewValue;
            caption.Text = $"{label} {setting}{suffix}";
            apply(setting);
        };
        if (label == "大小")
        {
            _sizeControls.Add(slider);
        }
        var row = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Margin = new Thickness(0, 3, 0, 3)
        };
        row.Children.Add(caption);
        row.Children.Add(slider);
        return new MenuItem { Header = row, StaysOpenOnClick = true };
    }

    private void SelectMode(SessionMotion? fixedMotion)
    {
        _autoFollowEnabled = fixedMotion is null;
        _autoFollowMenuItem.IsChecked = _autoFollowEnabled;
        foreach (var (motion, item) in _actionMenuItems)
        {
            item.IsChecked = fixedMotion == motion;
        }

        if (_fixedMotion == fixedMotion && _autoFollowEnabled == (fixedMotion is null))
        {
            return;
        }

        _fixedMotion = fixedMotion;
        _codexSessionActive = false;
        _activitySince = DateTimeOffset.UtcNow;
        RestartAnimation();
        if (fixedMotion is null)
        {
            RefreshCodexActivity();
        }
    }

    private void ToggleAutoFollow()
    {
        if (_autoFollowEnabled)
        {
            _autoFollowEnabled = false;
            _autoFollowMenuItem.IsChecked = false;
            _codexSessionActive = false;
            RestartAnimation();
            return;
        }

        SelectMode(null);
    }

    private void SetGlobalSize(int percent)
    {
        if (_sizePercent == percent)
        {
            return;
        }

        _sizePercent = percent;
        ApplySize(percent, PetWindowBounds.WorkArea(this));
        foreach (var slider in _sizeControls)
        {
            slider.Value = percent;
        }
    }

    private void SaveSize()
    {
        if (_sizePercent != _savedSizePercent && _sizeSettings.Save(_sizePercent))
        {
            _savedSizePercent = _sizePercent;
        }
    }

    private void PetImage_OnMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            SelectMode(_fixedMotion == SessionMotion.Typing ? null : SessionMotion.Typing);
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
        OpenContextMenu();
        e.Handled = true;
    }

    private void Window_OnPreviewMouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        OpenContextMenu();
        e.Handled = true;
    }

    private void Window_OnPreviewMouseRightButtonDown(object sender, MouseButtonEventArgs e)
    {
        OpenContextMenu();
        e.Handled = true;
    }

    private void OpenContextMenu()
    {
        if (ContextMenu is { } menu)
        {
            menu.PlacementTarget = this;
            menu.IsOpen = true;
        }
    }

    private sealed record MotionClip(ImageSource[] Frames, int[] EndTimes)
    {
        public ImageSource FrameAt(TimeSpan elapsed, bool loop) =>
            Frames[AnimationTiming.FrameAt(EndTimes, elapsed, loop)];
    }
}
