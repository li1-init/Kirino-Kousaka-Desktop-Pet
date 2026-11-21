# 桐乃独立桌面宠物

这个程序复用仓库中的 `windows/assets/` 下的图集和动画素材。构建时会生成独立程序所需的 PNG 和时长数据。自动跟随只使用本机进程、日志状态和文件锁。

程序会结合 `codex.exe` 进程、`CODEX_HOME/thread-writer-locks` 中的线程锁和会话日志最后状态判断 Codex 是否有活动会话。日志中的完成或中断记录会排除已经结束的旧线程，线程锁可以覆盖模型长时间思考、日志暂时没有新内容的情况。检测到活动会话时持续播放敲键盘动作。连续工作两分钟后播放一轮坐着看向你的思考动作，约五秒后回到敲键盘。会话结束后回到待机。

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

- 「等待」「审查」分别播放抱臂回望和展示游戏盒。「抱盒微笑」和原来的「跳跃」均可单独选择。

自动跟随约每两秒检查一次。它依赖本地 Codex 版本提供的日志和线程锁。远程任务、其他用户的会话或尚无本地状态记录的任务可能无法识别。两分钟打字、五秒回望的周期适用于独立程序。
