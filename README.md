# 桐乃桌面宠物

这个项目保存高坂桐乃 Chibi 桌面宠物的动作素材、Codex 原生宠物包，以及一个可以脱离 Codex 独立运行的 Windows 桌面程序。

项目现在分为两个使用部分。两部分共用同一套桐乃动作素材，但安装方式和运行环境彼此独立。

## v1.0.0 下载与动作预览

[GitHub Releases 下载](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet/releases)提供独立 Windows ZIP 和 Codex 原生 ZIP。更新详情见 [CHANGELOG.md](CHANGELOG.md)。

| 抱臂回望 | 展示游戏盒 | 抱盒微笑 |
| --- | --- | --- |
| ![桐乃抱臂并回望](previews/arms-crossed.png) | ![桐乃举起游戏盒](previews/show-game.png) | ![桐乃抱着游戏盒微笑](previews/hug-game.png) |

[三段连贯动作 GIF](previews/kirino-motion-preview.gif) · [高清站姿与打字对比](previews/kirino-hd-preview.png)

## 第一部分：Codex 原生宠物

这一部分使用 Codex 原生宠物格式，将桐乃安装到本机 Codex 的宠物目录。

### 主要文件

| 路径 | 内容 |
| --- | --- |
| `pet/pet.json` | Codex 宠物清单，ID 为 `kirino-chibi` |
| `pet/spritesheet.webp` | 透明桐乃动作图集 |
| `scripts/Restore-Pet.ps1` | 安装指定 Git 版本或回滚宠物 |
| `releases/kirino-codex-pet.zip` | 可分发的原生宠物资源包 |
| `runtime/` | 笔记本动作、思考动作和相关运行时素材 |
| `previews/` | 动作预览和桌面时序预览 |
| `qa/` | 图集、帧动画和会话状态校验 |

### 安装到 Codex

在仓库根目录执行：

```powershell
.\scripts\Restore-Pet.ps1 -Revision v1.0.0
```

脚本默认安装到：

```text
%USERPROFILE%\.codex\pets\kirino-chibi
```

如果设置了 `CODEX_HOME`，脚本会使用：

```text
%CODEX_HOME%\pets\kirino-chibi
```

安装完成后，在 Codex 的宠物设置中刷新。也可以指定某一个提交或标签进行安装：

```powershell
.\scripts\Restore-Pet.ps1 -Revision 7fb4def
```

脚本只安装并校验 `pet.json` 和 `spritesheet.webp`，并在替换失败时尝试恢复备份。三段新增动作分别使用原生图集的等待、审查和跳跃槽位。Codex 客户端决定这些状态何时触发和播放多久。

## 第二部分：独立 Windows 桌面程序

独立程序位于 [`standalone/`](standalone/)。它是一个 .NET 10 WPF 应用，使用自包含 `win-x64` 方式发布，可以直接在 Windows 上运行。

### 独立程序功能

- 透明背景、置顶显示和无任务栏窗口。
- 左键拖动桐乃。
- 双击桐乃切换待机和工作动作。
- 右键菜单切换待机、工作、抱臂回望、展示游戏盒、抱盒微笑、挥手、跳跃和失败。
- 右键菜单可开启和关闭自动跟随 Codex 会话。
- 自动检查本机 `codex.exe` 是否运行。
- 检查 `CODEX_HOME/thread-writer-locks` 中的线程锁。
- 检查会话日志最后状态，排除已经完成或中断的旧会话。
- Codex 会话运行时循环播放 `laptop-typing`。
- 连续工作两分钟后播放 `laptop-thinking`。
- 坐着看向你约五秒后回到敲键盘动作。
- 会话结束后回到待机动作。
- 使用桐乃 Q 版图标生成桌面快捷方式。

源码构建时会将共用的 WebP 图集和动作转换成 PNG 精灵表，并保留打字和思考的逐帧时长。

### 构建独立程序

构建需要 .NET 10 SDK 和可运行 Pillow 的 Python 3。进入 `standalone` 目录执行以下命令。

```powershell
python -m pip install -r requirements.txt
dotnet publish -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=false -o publish
```

发布后的程序位于：

```text
standalone\publish\KirinoDesktopPet.exe
```

如果需要分发，可以将 `publish` 目录压缩成 ZIP。发布目录包含自包含运行时，目标电脑不需要安装 .NET 或 Codex。

### 独立程序文件

| 路径 | 内容 |
| --- | --- |
| `standalone/KirinoDesktopPet.csproj` | WPF 项目和资源引用 |
| `standalone/MainWindow.xaml` | 透明置顶窗口 |
| `standalone/MainWindow.xaml.cs` | 动画、拖动、菜单和自动动作 |
| `standalone/CodexActivityMonitor.cs` | Codex 会话检测 |
| `standalone/assets/kirino.ico` | 桌面快捷方式图标 |
| `standalone/动作名称.md` | 动作和表情名称清单 |
| `standalone/README.md` | 独立程序的构建和操作说明 |

## 动作名称

### 原生图集动作

`idle`、`running-right`、`running-left`、`waving`、`jumping`、`failed`、`waiting`、`running`、`review`、`look-000-to-157.5`、`look-180-to-337.5`

### 笔记本动作

`laptop-typing`、`laptop-thinking`、`laptop-strip`、`laptop-session`、`laptop-work`、`laptop-glance`

完整说明、含义、帧数和图集位置见 [`standalone/动作名称.md`](standalone/%E5%8A%A8%E4%BD%9C%E5%90%8D%E7%A7%B0.md)。

## 项目目录

| 目录 | 用途 |
| --- | --- |
| `pet/` | Codex 原生宠物清单和图集 |
| `standalone/` | 独立 Windows 桌面程序 |
| `runtime/` | 运行时动画和会话状态素材 |
| `source/` | 动作源图、拆帧文件和构建脚本 |
| `previews/` | 动作预览和时序预览 |
| `qa/` | 自动化测试和验证结果 |
| `releases/` | 原生宠物分发包 |
| `scripts/` | Codex 宠物安装和恢复脚本 |
| `docs/` | 交接说明和项目记录 |
| `archive/` | 历史版本和回滚素材 |

## 验证

会话状态测试：

```powershell
node --test qa/session-activity.test.mjs
python qa/verify-release-assets.py
dotnet run --project qa/standalone -c Release -- --ui
```

独立程序的 Windows 测试覆盖窗口和菜单、会话状态及动画周期。真实 Codex 会话的识别依赖本机进程、日志和线程锁，具体范围见 [独立程序说明](standalone/README.md)。

## 参与开发

[贡献指南](CONTRIBUTING.md)规定提交格式、问题和修复说明、新增功能报告以及发版规则。每次发布在 [更新记录](CHANGELOG.md)中记录修复与新增。

## 当前边界

当前版本提供桌宠动作和本机会话跟随。大模型对话、启动问候和气泡文本尚未实现。
