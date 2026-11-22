# 桐乃独立桌面宠物

这个程序复用仓库中的 `windows/assets/` 下的图集和动画素材。构建时会生成独立程序所需的 PNG 和时长数据。自动跟随只使用本机进程、日志状态和文件锁。

程序会结合本机 Codex 进程、线程文件锁和会话日志判断任务状态。活跃时循环播放坐垫版打字，每 30 秒播放一次看屏幕思考，每两分钟优先播放回眸、脸红、嘟嘴。播完继续打字。没有活跃会话时循环播放“趴着打电话”待机动画。

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
- 右键打开多级动作菜单。一级选择「敲笔记本」「看屏幕思考」或「回眸脸红嘟嘴」，二级菜单提供统一的大小滑块和该动作独立的速度滑块。大小为 50% 至 200%，速度为 50% 至 150%。自动跟随和固定动作互斥，当前生效模式前会显示一个对号。固定动作会持续循环播放。
- 「回眸脸红嘟嘴」的二级菜单还提供触发间隔滑块，可在 30 至 600 秒之间调整，默认 120 秒。打字和思考的会话间隔分别为立即开始和每 30 秒，动作速度只影响播放时长。
- 右键菜单中的“自动跟随 Codex 会话”可以恢复或暂停自动跟随。
- 选择「退出」关闭程序。
- 同一个 Windows 登录会话只启动一个桐乃。再次打开时会提示已有桌宠运行。

自动跟随约每两秒检查一次。远程任务或其他用户的会话可能无法识别。点击一级动作名称会切换到该固定动作，并关闭自动跟随。坐垫版、木凳版及其它动作见[动作素材包](assets/kirino-kyosuke-motion/README.md)。
