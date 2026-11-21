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

安装当前的指尖打字版。

```powershell
& .\scripts\Restore-Pet.ps1 -Revision laptop-glance-2026-11-20
```

脚本默认安装到 `CODEX_HOME/pets/kirino-chibi`，未设置 `CODEX_HOME` 时使用用户目录中的 `.codex/pets/kirino-chibi`。安装后在 Codex 的宠物设置里刷新。账号宠物的原始图集保存在 `archive/pre-upgrade/active-account.png`，本地恢复脚本只操作本地安装文件。

## 重建早期图集

在有 Python、Pillow 和 `imageio-ffmpeg` 的环境中运行 `python source/build_upgrade.py`。结果写入 `build/`，其中的 `kirino-chibi/` 需要验证后再复制到 `pet/`。10 秒预览用于看清动作，Codex 桌面浮窗的播放时间由客户端控制。

## 早期桌面时序验证

提交 `e75352d` 保留了 10 秒站立思考候选及其测试。当前候选渲染器使用下文的笔记本任务节奏。

## 无气泡思考和待机眨眼

上一版（`calm-idle-2026-11-20`）使用透明动态 WebP，维持 V2 的 11 行布局。待机约 5.5 秒一轮，含呼吸、半闭、闭合和睁眼。视线跟随图也保留了短暂的眨眼。思考帧使用无气泡的固定托腮姿态，眼神缓慢移开再回落。客户端仍决定何时进入和退出思考状态。

运行 `python -B source/build_calm.py` 可以重建上一版的安装包。预览见 `previews/idle-blink.gif`、`previews/look-blink.gif` 和 `previews/calm-thinking.gif`，构建结果写到 `build/calm-take/`。要恢复之前的气泡版，可以把安装脚本的标签改为 `thinking-bubble-2026-11-20`。

## 侧倾思考和单独眨眼

运行 `python -B source/build_pose_laptop.py` 可重建侧倾思考版，需要 Pillow、imageio-ffmpeg、NumPy 和 OpenCV。结果写到 `build/pose-and-laptop/`。侧倾思考版从无气泡的托腮关键帧生成一轮约 7.2 秒的放松、压肩、侧倾、停顿和回正，鞋底保持在同一水平线。站立眨眼只覆盖眼睛区域。账号同步图集通过 Codex 原有时间表播放，浏览器和本地原生包可读取完整的动态图集。

### 玩笔记本预览

粉色笔记本参考插画外观。原著电击文库第一章记载桐乃喜欢妹系美少女游戏，并拿出《妹と恋しよっ♪》给京介看。动作以观看屏幕、敲键盘和按触控板表现阅读文字冒险。 [电击文库原著](https://dengekibunko.jp/novecomi/novel/16817330662080665881/16818093075678249306.html) · [笔记本参考插画](https://www.zerochan.net/1322875)

## 笔记本任务动作

上一版（`laptop-work-2026-11-20`）将 Codex 的运行状态素材换成坐姿敲键盘。只修补坐姿露出的鞋面区域，保留深色袜子。站立待机、跟随指针和其他动作与 `thinking-posture-2026-11-20` 的对应帧一致。运行 `python -B source/build_laptop_work.py` 可重建上一版的图集和预览，结果输出到 `build/laptop-work/`。

在 `runtime/thinking.css` 的状态预览中，任务开始立即启动 60 秒打字，随后播放 5 秒坐姿思考并重复。最后一个任务结束时立即停止该循环。确认无任务时，预览保留 6 秒后开始玩笔记本的空闲动作。打开 `qa/thinking-renderer.html` 可运行计时检查，动作见 `previews/laptop-typing.gif` 和 `previews/laptop-seated-thinking.gif`。

本机 Windows Codex `26.1117.3838.0` 默认在约 2.46 秒后复用待机帧。原生宠物包可以更新任务动作素材，桌面客户端没有加载候选 CSS 或设置会话分钟计时的入口。因此真实安装包在进入运行状态时使用新版打字帧，完整的 60 秒加 5 秒循环在浏览器状态预览中验证。 [Codex 原生宠物包格式](https://github.com/openai/skills/blob/main/skills/.curated/hatch-pet/references/codex-pet-contract.md)

## 指尖打字和回望表情

站姿思考和只动眼睛的待机预览原样保存在 `previews/thinking-body-motion.gif` 和 `previews/eyes-only-idle.gif`。站姿方案也保留在 `thinking-posture-2026-11-20` 标签。新版打字将变化限定在指尖和相邻按键处，手腕、手臂和坐姿保持固定。

5 秒的坐姿思考从看键盘开始，随后转头与观众对视，脸红、微皱眉、做短暂开口动作，再把视线转回屏幕。动作参考导演对桐乃性格的叙述和原著第四章对她脸红后转开视线的描写。 [动画官网导演访谈](https://www.oreimo-anime.com/1st/special/staff_comment01.html) · [电击文库原著](https://dengekibunko.jp/novecomi/novel/16817330662080665881/16818093075684923362.html)

坐姿新版动画使用静音 WebP 和 GIF。执行 `python -B source/build_laptop_session.py` 可生成 5 秒的协同思考动作和完整过渡预览。上身、肩肘和头部随视线一起转动，动作过渡约 60 帧每秒。桌面、笔记本、手和下半身使用原打字姿势对齐。

## 持续工作和交接

已安装的原生素材可由 `laptop-glance-2026-11-20` 还原。两个要保留的历史动画继续在 `previews/`。完整静音过渡见 `previews/laptop-task-silent.gif`。

使用 `python qa/probe-native-player.py <app.asar 路径>` 检查当前 Windows 客户端安装资源中的两个浮窗调用，复现 2.46 秒回退并验证内部持续循环参数。运行 `node --test qa/session-activity.test.mjs` 检查会话状态。浏览器夹具 `qa/thinking-renderer.html` 由会话事件聚合值驱动，忽略单独的视觉待机回退。它支持在本地 HTTP 静态服务器中运行。

原生浮窗尚未接入会话聚合和 65 秒静音周期。需要能够修改或扩展客户端渲染器的入口。最新交接说明包括安装版本、状态根因、实际验证范围、接入步骤和回滚命令，并可直接交给其他 AI 阅读。 [桐乃桌面宠物交接说明](docs/桐乃桌面宠物交接.md)
