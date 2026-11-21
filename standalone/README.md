# 桐乃独立桌面宠物

这个程序复用仓库中的 `pet/spritesheet.webp`、`runtime/laptop-typing.webp` 和 `runtime/laptop-thinking.webp`。它不读取 Codex 配置，也不需要接入 Codex 的插件接口。

程序会结合 `codex.exe` 进程、`CODEX_HOME/thread-writer-locks` 中的线程锁和会话日志最后状态判断 Codex 是否有活动会话。日志中的完成或中断记录会排除已经结束的旧线程，线程锁可以覆盖模型长时间思考、日志暂时没有新内容的情况。检测到活动会话时持续播放敲键盘动作。连续工作两分钟后播放一轮坐着看向你的思考动作，约五秒后回到敲键盘。会话结束后回到待机。

## 构建

在 `standalone` 目录执行：

```powershell
dotnet restore
dotnet publish -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=false -o publish
```

发布后的程序位于：

```text
publish\KirinoDesktopPet.exe
```

也可以直接使用仓库中已经生成的 `KirinoDesktopPet-win-x64.zip`。解压后运行 `KirinoDesktopPet.exe`，发布目录内包含自包含运行时，不需要安装 .NET 或 Codex。桌面快捷方式使用 `assets/kirino.ico` 生成的桐乃图标，并指向发布目录里的 EXE。

动作和表情的可用名称记录在 `动作名称.md`。

## 操作

- 左键拖动窗口。
- 双击桐乃，在待机和工作动作之间切换。
- 右键打开动作菜单。
- 右键菜单中的“自动跟随 Codex 会话”可以恢复或暂停自动跟随。
- 选择“退出桐乃桌面宠物”关闭程序。

动作帧来自原项目的 8×11 WebP 图集，状态映射沿用原始图集布局。
