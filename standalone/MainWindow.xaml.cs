namespace KirinoDesktopPet;

using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using WpfPoint = System.Windows.Point;
using ImageSharpImage = SixLabors.ImageSharp.Image;

public partial class MainWindow : Window
{
    private const int CellWidth = 192;
    private const int CellHeight = 208;
    private static readonly TimeSpan FrameInterval = TimeSpan.FromMilliseconds(100);
    private static readonly TimeSpan ActivityCheckInterval = TimeSpan.FromSeconds(2);
    private static readonly TimeSpan ThinkingInterval = TimeSpan.FromSeconds(5);
    private static readonly TimeSpan KeyboardInterval = TimeSpan.FromMinutes(2);

    private readonly DispatcherTimer _timer;
    private readonly Dictionary<PetState, int[]> _frames = new()
    {
        [PetState.Idle] = Enumerable.Range(0, 6).ToArray(),
        [PetState.Working] = Enumerable.Range(0, 6).ToArray(),
        [PetState.Waiting] = Enumerable.Range(0, 6).ToArray(),
        [PetState.Review] = Enumerable.Range(0, 6).ToArray(),
        [PetState.Failed] = Enumerable.Range(0, 8).ToArray(),
        [PetState.Waving] = Enumerable.Range(0, 4).ToArray(),
        [PetState.Jumping] = Enumerable.Range(0, 5).ToArray()
    };
    private readonly Dictionary<PetState, int> _rows = new()
    {
        [PetState.Idle] = 0,
        [PetState.WalkingRight] = 1,
        [PetState.WalkingLeft] = 2,
        [PetState.Waving] = 3,
        [PetState.Jumping] = 4,
        [PetState.Failed] = 5,
        [PetState.Waiting] = 6,
        [PetState.Working] = 7,
        [PetState.Review] = 8
    };
    private readonly Dictionary<(int Row, int Column), ImageSource> _sheetCache = new();
    private readonly Dictionary<string, ImageSource[]> _clipCache = new();
    private Image<Rgba32>? _sheet;
    private Image<Rgba32>? _typingClip;
    private Image<Rgba32>? _thinkingClip;
    private PetState _manualState = PetState.Idle;
    private AutoAnimation _autoAnimation = AutoAnimation.Idle;
    private bool _autoFollowCodex = true;
    private bool _codexSessionActive;
    private DateTime _lastActivityCheckUtc = DateTime.MinValue;
    private DateTime _keyboardCycleStartedUtc;
    private DateTime _thinkingStartedUtc;
    private int _frame;
    private WpfPoint _dragOffset;
    private MenuItem? _autoFollowMenuItem;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += OnClosed;
        _timer = new DispatcherTimer { Interval = FrameInterval };
        _timer.Tick += (_, _) => AdvanceAnimation();
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var assetRoot = Path.Combine(AppContext.BaseDirectory, "assets");
        _sheet = ImageSharpImage.Load<Rgba32>(Path.Combine(assetRoot, "spritesheet.webp"));
        _typingClip = ImageSharpImage.Load<Rgba32>(Path.Combine(assetRoot, "laptop-typing.webp"));
        _thinkingClip = ImageSharpImage.Load<Rgba32>(Path.Combine(assetRoot, "laptop-thinking.webp"));
        PositionAtBottomRight();
        BuildContextMenu();
        _keyboardCycleStartedUtc = DateTime.UtcNow;
        ShowFrame();
        _timer.Start();
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        _timer.Stop();
        _sheet?.Dispose();
        _typingClip?.Dispose();
        _thinkingClip?.Dispose();
    }

    private void PositionAtBottomRight()
    {
        var workArea = SystemParameters.WorkArea;
        Left = Math.Max(workArea.Left, workArea.Right - Width - 24);
        Top = Math.Max(workArea.Top, workArea.Bottom - Height - 24);
    }

    private void AdvanceAnimation()
    {
        var now = DateTime.UtcNow;
        if (now - _lastActivityCheckUtc >= ActivityCheckInterval)
        {
            _lastActivityCheckUtc = now;
            UpdateCodexActivity(CodexActivityMonitor.IsSessionActive(), now);
        }

        if (_autoFollowCodex && _codexSessionActive)
        {
            AdvanceAutomaticAnimation(now);
            return;
        }

        AdvanceManualAnimation();
    }

    private void UpdateCodexActivity(bool active, DateTime now)
    {
        if (active == _codexSessionActive)
        {
            return;
        }

        _codexSessionActive = active;
        _frame = 0;
        if (active)
        {
            _autoAnimation = AutoAnimation.Typing;
            _keyboardCycleStartedUtc = now;
        }
        else
        {
            _autoAnimation = AutoAnimation.Idle;
            _keyboardCycleStartedUtc = now;
        }

        ShowFrame();
    }

    private void AdvanceAutomaticAnimation(DateTime now)
    {
        if (_autoAnimation == AutoAnimation.Typing &&
            now - _keyboardCycleStartedUtc >= KeyboardInterval)
        {
            _autoAnimation = AutoAnimation.Thinking;
            _thinkingStartedUtc = now;
            _frame = 0;
        }
        else if (_autoAnimation == AutoAnimation.Thinking &&
                 now - _thinkingStartedUtc >= ThinkingInterval)
        {
            _autoAnimation = AutoAnimation.Typing;
            _keyboardCycleStartedUtc = now;
            _frame = 0;
        }

        _frame++;
        ShowFrame();
    }

    private void AdvanceManualAnimation()
    {
        var available = _frames.TryGetValue(_manualState, out var frames)
            ? frames
            : _frames[PetState.Idle];
        _frame = (_frame + 1) % available.Length;
        ShowFrame();
    }

    private void ShowFrame()
    {
        if (_autoFollowCodex && _codexSessionActive)
        {
            ShowAutomaticFrame();
            return;
        }

        ShowSheetFrame(_manualState, _frame);
    }

    private void ShowAutomaticFrame()
    {
        if (_autoAnimation == AutoAnimation.Thinking)
        {
            PetImage.Source = GetClipFrame("thinking", _thinkingClip, _frame);
        }
        else
        {
            PetImage.Source = GetClipFrame("typing", _typingClip, _frame);
        }
    }

    private ImageSource GetClipFrame(string name, Image<Rgba32>? clip, int frame)
    {
        if (clip is null || clip.Frames.Count == 0)
        {
            return GetSheetFrame(PetState.Idle, 0);
        }

        if (!_clipCache.TryGetValue(name, out var frames))
        {
            frames = Enumerable.Range(0, clip.Frames.Count)
                .Select(index => CreateFrame(clip.Frames[index]))
                .ToArray();
            _clipCache[name] = frames;
        }

        return frames[frame % frames.Length];
    }

    private void ShowSheetFrame(PetState state, int frame)
    {
        PetImage.Source = GetSheetFrame(state, frame);
    }

    private ImageSource GetSheetFrame(PetState state, int frame)
    {
        if (_sheet is null)
        {
            return PetImage.Source ?? throw new InvalidOperationException("The sprite sheet is not loaded.");
        }

        var row = _rows.TryGetValue(state, out var rowIndex) ? rowIndex : 0;
        var available = _frames.TryGetValue(state, out var frames) ? frames : _frames[PetState.Idle];
        var column = available[Math.Clamp(frame, 0, available.Length - 1)];
        if (!_sheetCache.TryGetValue((row, column), out var source))
        {
            source = CreateSheetFrame(row, column);
            _sheetCache[(row, column)] = source;
        }

        return source;
    }

    private BitmapSource CreateSheetFrame(int row, int column)
    {
        if (_sheet is null)
        {
            throw new InvalidOperationException("The sprite sheet is not loaded.");
        }

        return CreateFrame(_sheet.Frames.RootFrame, row * CellHeight, column * CellWidth, CellWidth, CellHeight);
    }

    private BitmapSource CreateFrame(ImageFrame<Rgba32> frame)
    {
        return CreateFrame(frame, 0, 0, frame.Width, frame.Height);
    }

    private BitmapSource CreateFrame(
        ImageFrame<Rgba32> frame,
        int top,
        int left,
        int width,
        int height)
    {
        var pixels = new byte[width * height * 4];
        frame.ProcessPixelRows(accessor =>
        {
            for (var y = 0; y < height; y++)
            {
                var sourceRow = accessor.GetRowSpan(top + y).Slice(left, width);
                var destinationOffset = y * width * 4;
                for (var x = 0; x < width; x++)
                {
                    var pixel = sourceRow[x];
                    var offset = destinationOffset + x * 4;
                    pixels[offset] = pixel.B;
                    pixels[offset + 1] = pixel.G;
                    pixels[offset + 2] = pixel.R;
                    pixels[offset + 3] = pixel.A;
                }
            }
        });

        var bitmap = BitmapSource.Create(
            width,
            height,
            96,
            96,
            PixelFormats.Bgra32,
            null,
            pixels,
            width * 4);
        bitmap.Freeze();
        return bitmap;
    }

    private void SetManualState(PetState state)
    {
        _autoFollowCodex = false;
        _manualState = state;
        _frame = 0;
        UpdateAutoFollowMenu();
        ShowFrame();
    }

    private void EnableAutoFollow()
    {
        _autoFollowCodex = true;
        _frame = 0;
        _keyboardCycleStartedUtc = DateTime.UtcNow;
        _autoAnimation = _codexSessionActive ? AutoAnimation.Typing : AutoAnimation.Idle;
        UpdateAutoFollowMenu();
        ShowFrame();
    }

    private void BuildContextMenu()
    {
        var menu = new ContextMenu();
        _autoFollowMenuItem = new MenuItem { Header = "自动跟随 Codex 会话", IsCheckable = true };
        _autoFollowMenuItem.Click += (_, _) => EnableAutoFollow();
        menu.Items.Add(_autoFollowMenuItem);
        menu.Items.Add(new Separator());
        AddStateItem(menu, "待机", PetState.Idle);
        AddStateItem(menu, "工作 / 敲笔记本", PetState.Working);
        AddStateItem(menu, "等待", PetState.Waiting);
        AddStateItem(menu, "审查", PetState.Review);
        AddStateItem(menu, "挥手", PetState.Waving);
        AddStateItem(menu, "跳跃", PetState.Jumping);
        AddStateItem(menu, "失败", PetState.Failed);
        menu.Items.Add(new Separator());
        var exit = new MenuItem { Header = "退出桐乃桌面宠物" };
        exit.Click += (_, _) => Close();
        menu.Items.Add(exit);
        PetImage.ContextMenu = menu;
        UpdateAutoFollowMenu();
    }

    private void UpdateAutoFollowMenu()
    {
        if (_autoFollowMenuItem is not null)
        {
            _autoFollowMenuItem.IsChecked = _autoFollowCodex;
        }
    }

    private void AddStateItem(ContextMenu menu, string label, PetState state)
    {
        var item = new MenuItem { Header = label };
        item.Click += (_, _) => SetManualState(state);
        menu.Items.Add(item);
    }

    private void PetImage_OnMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            SetManualState(_manualState == PetState.Working ? PetState.Idle : PetState.Working);
            return;
        }

        _dragOffset = e.GetPosition(this);
        PetImage.CaptureMouse();
        MouseMove += OnDrag;
        MouseLeftButtonUp += OnDragEnd;
    }

    private void OnDrag(object sender, MouseEventArgs e)
    {
        if (e.LeftButton != MouseButtonState.Pressed)
        {
            OnDragEnd(sender, e);
            return;
        }

        var position = PointToScreen(e.GetPosition(this));
        Left = position.X - _dragOffset.X;
        Top = position.Y - _dragOffset.Y;
    }

    private void OnDragEnd(object? sender, MouseEventArgs e)
    {
        PetImage.ReleaseMouseCapture();
        MouseMove -= OnDrag;
        MouseLeftButtonUp -= OnDragEnd;
    }

    private void PetImage_OnMouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (PetImage.ContextMenu is not null)
        {
            PetImage.ContextMenu.IsOpen = true;
        }
        e.Handled = true;
    }

    private enum AutoAnimation
    {
        Idle,
        Typing,
        Thinking
    }

    private enum PetState
    {
        Idle,
        Working,
        Waiting,
        Review,
        Failed,
        Waving,
        Jumping,
        WalkingRight,
        WalkingLeft
    }
}
