# 桐乃桌面宠物

这是高坂桐乃 Codex 原生宠物的本地 Git 仓库。

| 目录 | 内容 |
| --- | --- |
| `pet/` | 当前版本的 `pet.json` 和透明 WebP 图集 |
| `source/` | 动作源条、拆帧和图集构建脚本 |
| `previews/` | 动作总览、10 秒思考预览和桌面时序预览 |
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

恢复带思考气泡的版本。

```powershell
& .\scripts\Restore-Pet.ps1 -Revision thinking-bubble-2026-11-20
```

脚本默认安装到 `CODEX_HOME/pets/kirino-chibi`，未设置 `CODEX_HOME` 时使用用户目录中的 `.codex/pets/kirino-chibi`。安装后在 Codex 的宠物设置里刷新。账号宠物的原始图集保存在 `archive/pre-upgrade/active-account.png`，本地恢复脚本只操作本地安装文件。

## 重建当前图集

在有 Python、Pillow 和 `imageio-ffmpeg` 的环境中运行 `python source/build_upgrade.py`。结果写入 `build/`，其中的 `kirino-chibi/` 需要验证后再复制到 `pet/`。10 秒预览用于看清动作，Codex 桌面浮窗的播放时间由客户端控制。
