# 桐乃独立桌面宠物

这个程序复用仓库中的 `windows/assets/` 下的图集和动画素材。构建时会生成独立程序所需的 PNG 和时长数据。自动跟随只使用本机进程、日志状态和文件锁。

程序会结合本机 Codex 进程、线程文件锁和会话日志判断任务状态。工作时左右手分组敲键并短暂停读，连续工作两分钟后会回望约五秒。每次成功结束播放一遍屈膝、跃起与落地，失败时播放低头、垂肩和恢复站姿。反馈结束后，其他任务还在运行就继续打字，否则回到待机。主动取消会直接结束当前工作状态。

## 构建

安装 .NET 10 SDK 和 Python 3 后，在 `windows/app` 目录执行以下命令。

```powershell
python -m pip install -r requirements.txt
dotnet publish -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=false -o publish
```

发布后的程序位于：

```text
publish\KirinoDesktopPet.exe
```

也可以在 [GitHub Releases](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet/releases)下载 `KirinoDesktopPet-win-x64.zip`。完整解压后运行 `KirinoDesktopPet.exe`，发布目录内包含自包含运行时，可以在没有 .NET SDK、Python 或 Codex 的 Windows 上使用手动动作。

构建后在 `windows/app` 目录运行 `.\Create-DesktopShortcut.ps1`，即可在桌面创建带桐乃图标的快捷方式。解压 ZIP 后使用 `-Executable` 指定解压目录里的 EXE。

动作和表情的可用名称记录在 [动作名称](app/动作名称.md)。

## 操作

- 左键拖动窗口。
- 双击桐乃，在待机和工作动作之间切换。
- 右键打开动作菜单。
- 右键菜单中的“自动跟随 Codex 会话”可以恢复或暂停自动跟随。
- 选择“退出桐乃桌面宠物”关闭程序。
- 同一个 Windows 登录会话只启动一个桐乃。再次打开时会提示已有桌宠运行。

- 「等待」「审查」分别播放抱臂回望和展示游戏盒。「抱盒微笑」和原来的「跳跃」均可单独选择。

自动跟随约每两秒检查一次。它从启用跟随起监听本机会话结束事件。远程任务、其他用户的会话或缺少本地结束记录的任务可能无法识别。六组新动作见 [v1.1.0 预览](previews/windows-motion-v1.1.0.webp)。
