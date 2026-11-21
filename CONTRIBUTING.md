# 贡献指南

## 开发范围与项目结构

当前接受独立 Windows 桌面宠物的开发。新代码、素材、预览、测试分别放到 `windows/app/`、`windows/assets/`、`windows/previews/`、`windows/tests/`。Windows 构建只引用 `windows/` 内的项目资源。`codex/` 保存暂停维护的原生宠物，恢复开发由项目负责人决定。

所有公开贡献提交到 [Kirino-Kousaka-Desktop-Pet](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet)。提交标题格式为 `类型(范围): 简短描述`，可用类型 `fix`、`feat`、`docs`、`test`、`chore`，范围可用 `windows`、`art` 或 `release`。例如 `fix(windows): 修复待机动画切换`。

## 按版本记录改动

提交正文和 PR 模板都要写目标版本、解决了什么问题、新加入了什么功能和验证结果。更新 `CHANGELOG.md` 的「未发布」，发版时将该版内容移到版本标题下。某一项没有内容就写「无」。Windows 预览相关改动附图片或动画，验证透明度、帧数和时长。

```markdown
## v1.1.1 · YYYY-MM-DD

### 解决了什么问题

- 修复长时间待机后首次点击没反应，恢复点击时刷新动画状态。

### 新加入了什么功能

- 无。
```

版本号使用 `主版本.次版本.修订号`。兼容修复升修订号，兼容新功能升次版本，破坏现有兼容性时升主版本。发版时让 `windows/app/KirinoDesktopPet.csproj` 的 `<Version>`、`CHANGELOG.md` 中的版本和 Git 标签保持一致。

GitHub Actions 检查 PR 是否填写模板、更新日志并遵守归档边界，也会验证 Windows 构建和测试。合并前须通过这些检查。在 `main` 通过 Windows 验收后，先推送分支，再单独推送标签。发布流程生成 Windows x64 ZIP。

```powershell
git push origin main
git tag -a v1.1.1 -m "桐乃桌面宠物 v1.1.1"
git push origin refs/tags/v1.1.1
```

报告问题时填写运行版本、Windows 版本、复现步骤、预期和实际行为。附截图前请遮住个人信息。[问题与功能建议](https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet/issues/new/choose)
