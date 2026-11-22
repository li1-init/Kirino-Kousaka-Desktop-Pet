# 桐乃桌面宠物

这是一个独立运行的 Windows 桌面宠物项目。Windows 版是当前开发和发布主线。Codex 原生宠物已暂停，历史代码和安装包保存在 [codex/](codex/README.md)。

## 下载与运行

在 [GitHub Releases](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet/releases) 下载 `KirinoDesktopPet-win-x64.zip`，完整解压后运行 `KirinoDesktopPet.exe`。发布包内含 Windows x64 运行时，可以在没有 Codex、.NET SDK 或 Python 的电脑上使用。

左键拖动桐乃，双击在待机和打字之间切换。右键打开多级动作菜单，一级选择敲笔记本、看屏幕思考或回眸脸红嘟嘴，二级调整统一大小、该动作速度和回眸触发间隔。自动跟随和固定动作互斥，当前模式前显示一个对号。固定动作会持续循环播放。回眸动作默认每 120 秒触发一次。没有活跃 Codex 会话时循环播放“趴着打电话”待机动画。菜单同时提供退出。大小范围为 50% 至 200%，会话跟随使用本机状态判断任务是否活动，默认播放坐垫版动作。

| 抱臂回望 | 展示游戏盒 | 抱盒微笑 |
| --- | --- | --- |
| ![桐乃抱臂并回望](windows/previews/arms-crossed.png) | ![桐乃举起游戏盒](windows/previews/show-game.png) | ![桐乃抱着游戏盒微笑](windows/previews/hug-game.png) |

[v1.1.0 六组动作实播](windows/previews/windows-motion-v1.1.0.webp) · [早期动作 GIF](windows/previews/kirino-motion-preview.gif)

## 项目结构

| 目录 | 用途 |
| --- | --- |
| `windows/app/` | .NET 10 WPF 程序、构建脚本和快捷方式脚本 |
| `windows/assets/` | Windows 程序的动画图集、动画源和帧时长来源 |
| `windows/previews/` | Windows 首页代表图和预览 |
| `windows/tests/` | Windows 窗口、菜单、动画时序、会话检测和素材校验 |
| `codex/` | 暂停维护的 Codex 原生宠物项目和历史安装包 |
| `.github/` | 提交模板、Windows 校验和发布流程 |

Windows 的构建、测试和发布材料都从 `windows/` 读取。开发和发版请遵循[贡献指南](CONTRIBUTING.md)。每个版本的修复与新增见[更新记录](CHANGELOG.md)。

## 构建与验证

安装 .NET 10 SDK 和 Python 3 后，在仓库根目录运行以下命令。

```powershell
python -m pip install -r windows/app/requirements.txt
python windows/tests/verify-assets.py
dotnet run --project windows/tests -c Release -- --ui
dotnet publish windows/app -c Release -r win-x64 --self-contained true -o windows/app/publish
```

构建后可以运行 `windows/app/publish/KirinoDesktopPet.exe`，也可以运行 `windows/app/Create-DesktopShortcut.ps1` 创建桌面快捷方式。操作、会话跟随范围见 [Windows 使用说明](windows/README.md)。
