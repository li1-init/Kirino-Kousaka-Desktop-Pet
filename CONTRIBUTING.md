# 贡献指南

报告问题时写明版本、使用方式（Codex 原生版或独立 Windows 版）、重现步骤、预期和实际行为。截图可帮助定位动画问题，请先遮住个人信息。使用 [GitHub Issues](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet/issues/new/choose) 提交。

## 提交与 Pull Request

用 `类型(范围): 简短描述` 写提交标题。类型用 `fix`、`feat`、`docs`、`test` 或 `chore`，范围可用 `codex`、`standalone`、`art` 或 `release`。例如 `fix(standalone): 按素材帧时长播放坐姿思考`。

提交正文或 Pull Request 填写项目模板中的三个部分。

1. **发现的问题和修复**。写清问题表现、原因和修复方式。只有新功能时填「无」。
2. **新增功能**。写清使用者会看到什么变化。只有修复时填「无」。
3. **验证结果**。写出运行的命令、测试过的系统、动作或安装步骤，并记录尚未验证的情况。

更新 [CHANGELOG.md](CHANGELOG.md) 的「未发布」部分。修改素材时附一张代表图或一段动画预览，并核对透明度、动作所用的图集行和受其影响的安装包。

## 版本和发布

使用 `主版本.次版本.修订号`。

| 本次发布的最高影响 | 调整方式 |
| --- | --- |
| 修复、依赖安全更新或对外发布的文档更正 | 增加修订号，例如 `1.0.0` → `1.0.1` |
| 新动作或其他兼容的用户功能 | 增加次版本，修订号归零，例如 `1.0.1` → `1.1.0` |
| 破坏已有安装、兼容性或项目约定的改动 | 增加主版本，次版本和修订号归零，例如 `1.1.0` → `2.0.0` |

维护者在发布提交中把「未发布」条目移到有版本和日期的章节，在 `standalone/KirinoDesktopPet.csproj` 同步 `<Version>`，核对 README 的下载说明，并重新验收安装包。`pet/pet.json` 中的 `spriteVersionNumber` 是 Codex 图集格式版本。保持 `2`，直到目标图集格式本身发生变化。

从已验证的 `main` 发布提交打 `v<版本号>` 标签，并推送到 GitHub。GitHub Actions 会核对版本、运行测试并上传两个 ZIP。保留已有标签和发布记录。

```powershell
git tag -a v1.0.1 -m "桐乃桌面宠物 v1.0.1"
git push origin v1.0.1
```

验收命令和源码构建要求见 [README](README.md#验证) 与 [独立程序说明](standalone/README.md)。
