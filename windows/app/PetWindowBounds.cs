namespace KirinoDesktopPet;

using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

internal static class PetWindowBounds
{
    internal static Rect WorkArea(Window window)
    {
        const uint nearestMonitor = 2;
        var monitor = MonitorFromWindow(new WindowInteropHelper(window).Handle, nearestMonitor);
        var info = new MonitorInfo { Size = Marshal.SizeOf<MonitorInfo>() };
        if (monitor == IntPtr.Zero || !GetMonitorInfo(monitor, ref info))
        {
            return SystemParameters.WorkArea;
        }

        var start = window.PointFromScreen(new Point(info.Work.Left, info.Work.Top));
        var end = window.PointFromScreen(new Point(info.Work.Right, info.Work.Bottom));
        var origin = new Vector(window.Left, window.Top);
        return new Rect(start + origin, end + origin);
    }

    internal static Rect Resize(Rect window, Rect workArea, Size baseSize, int percent)
    {
        var scale = Math.Min(percent / 100.0, Math.Min(workArea.Width / baseSize.Width, workArea.Height / baseSize.Height));
        var width = Math.Min(baseSize.Width * scale, workArea.Width);
        var height = Math.Min(baseSize.Height * scale, workArea.Height);
        var left = Math.Clamp(window.Left + (window.Width - width) / 2, workArea.Left,
            Math.Max(workArea.Left, workArea.Right - width));
        var top = Math.Clamp(window.Bottom - height, workArea.Top, Math.Max(workArea.Top, workArea.Bottom - height));
        return new Rect(left, top, width, height);
    }

    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);

    [DllImport("user32.dll", EntryPoint = "GetMonitorInfoW", ExactSpelling = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetMonitorInfo(IntPtr monitor, ref MonitorInfo info);

    [StructLayout(LayoutKind.Sequential)]
    private struct MonitorInfo
    {
        public int Size;
        public NativeRect Bounds;
        public NativeRect Work;
        public uint Flags;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect
    {
        public int Left, Top, Right, Bottom;
    }
}
