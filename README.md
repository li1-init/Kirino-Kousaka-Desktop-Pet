# 桐乃桌面宠物

这是高坂桐乃 Codex 原生宠物的本地 Git 仓库。

| 目录 | 内容 |
| --- | --- |
| `pet/` | 当前版本的 `pet.json` 和透明 WebP 图集 |
| `source/` | 动作源条、拆帧和图集构建脚本 |
| `previews/` | 动作总览、10 秒思考预览和桌面时序预览 |
| `releases/` | 可直接解压安装的宠物 ZIP |
| `qa/` | 帧和图集校验结果 |
| `references/` | 用户提供的桐乃原始包和 Rem 参考教程 |
| `archive/` | 升级前的完整回滚包、账号原素材和早期动作试验 |
| `scripts/` | 从 Git 提交安装或回滚本地宠物的脚本 |

## 更新和回滚

先用 `git status` 检查未提交修改。更新素材后先验证图集和预览，再提交本次改动。每个可用版本保留一个标签。用 `git log --oneline --decorate` 查看版本。

在项目目录运行下面的命令，会把升级前的导出版本安装到本地 Codex。脚本直接从 Git 读取安装文件，保留当前分支、提交历史和工作区的修改。

```powershell
& .\scripts\Restore-Pet.ps1 -Revision before-thinking-upgrade
```

安装当前的无气泡思考和待机眨眼版。

```powershell
& .\scripts\Restore-Pet.ps1 -Revision calm-idle-2026-11-20
```

脚本默认安装到 `CODEX_HOME/pets/kirino-chibi`，未设置 `CODEX_HOME` 时使用用户目录中的 `.codex/pets/kirino-chibi`。安装后在 Codex 的宠物设置里刷新。账号宠物的原始图集保存在 `archive/pre-upgrade/active-account.png`，本地恢复脚本只操作本地安装文件。

## 重建当前图集

在有 Python、Pillow 和 `imageio-ffmpeg` 的环境中运行 `python source/build_upgrade.py`。结果写入 `build/`，其中的 `kirino-chibi/` 需要验证后再复制到 `pet/`。10 秒预览用于看清动作，Codex 桌面浮窗的播放时间由客户端控制。

## 10 秒思考循环的桌面渲染验证

`runtime/thinking.css` 是给桌面浮窗渲染器的集成候选。它依靠客户端已有的宠物 ID 和状态属性，只在本地桐乃处于 `running` 时播放。每轮 10 秒，任务继续时重复。任务完成、等待输入或失败时移交给客户端的对应动作，短任务提前结束时立即取消循环。桌面渲染器接入时可用 `data-kirino-animation-paused="true"` 传递原生暂停状态。系统开启减少动画时不启用循环。

在 `previews/thinking-state-loop.gif` 可查看待机、连续两轮思考、回到待机的演示。用浏览器打开 `qa/thinking-renderer.html` 可以运行时序检查。测试使用真实桐乃图集和同样的状态属性，覆盖客户端在 2.46 秒写入待机帧、持续运行超过两轮、短任务结束、原生暂停和其他宠物。

已检查 Windows Codex `26.1117.3838.0` 的安装资源。宠物包只提供名称、图集等数据，应用没有加载用户宠物样式表的入口。已安装的 Microsoft Store 包在 WindowsApps 的受保护目录中，Electron 也启用了 ASAR 完整性校验。此候选目前属于项目内验证，尚未接入桌面客户端。

- [Codex 原生宠物包格式](https://github.com/openai/skills/blob/main/skills/.curated/hatch-pet/references/codex-pet-contract.md)
- [Windows MSIX 安装目录保护](https://learn.microsoft.com/en-us/windows/msix/msix-containerization-overview)
- [Electron ASAR 完整性检查](https://www.electronjs.org/docs/latest/tutorial/asar-integrity)

## 无气泡思考和待机眨眼

当前原生安装包使用透明动态 WebP，维持 V2 的 11 行布局。待机约 5.5 秒一轮，含呼吸、半闭、闭合和睁眼。视线跟随图也保留了短暂的眨眼。思考帧使用无气泡的固定托腮姿态，眼神缓慢移开再回落。客户端仍决定何时进入和退出思考状态。

运行 `python -B source/build_calm.py` 可以从原画和上一版 Git 标签重建当前包。预览见 `previews/idle-blink.gif`、`previews/look-blink.gif` 和 `previews/calm-thinking.gif`，构建结果写到 `build/calm-take/`。要恢复之前的气泡版，可以把安装脚本的标签改为 `thinking-bubble-2026-11-20`。
