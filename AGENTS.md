# 桐乃桌面宠物

- 每次先检查 Git 状态和历史，保留用户已有修改。公开开发目标是 `https://github.com/li1-init/Kirino-Kousaka-Desktop-Pet.git`，日常开发使用跟踪公开仓库的分支。
- Windows 桌面宠物是主线。程序、素材、预览和测试分别放在 `windows/app/`、`windows/assets/`、`windows/previews/`、`windows/tests/`。Windows 构建、测试和发布不得依赖 `codex/`。
- `codex/` 是暂停维护的原生宠物归档。一般更新不得修改归档，恢复维护由项目负责人决定。
- 每次修改按 [CONTRIBUTING.md](CONTRIBUTING.md) 填写目标版本、解决的问题、新增功能与验证，维护 [CHANGELOG.md](CHANGELOG.md)，只提交本次相关文件。
- 发版保证 Windows 项目版本、更新记录与 `vX.Y.Z` 标签一致。运行 Windows 验收，分别推送分支和标签，保留历史版本。
