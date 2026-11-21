namespace KirinoDesktopPet;

public partial class App : System.Windows.Application
{
    private Mutex? _instance;

    protected override void OnStartup(System.Windows.StartupEventArgs e)
    {
        base.OnStartup(e);
        var candidate = new Mutex(false, @"Local\KirinoDesktopPet.SingleInstance", out var firstInstance);
        if (!firstInstance)
        {
            candidate.Dispose();
            System.Windows.MessageBox.Show("桐乃桌面宠物已经在运行，不能再打开一个。",
                "桐乃桌面宠物", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            Shutdown();
            return;
        }
        _instance = candidate;
        ShutdownMode = System.Windows.ShutdownMode.OnMainWindowClose;
        MainWindow = new MainWindow();
        MainWindow.Show();
    }

    protected override void OnExit(System.Windows.ExitEventArgs e)
    {
        _instance?.Dispose();
        base.OnExit(e);
    }
}
