# Security Policy

## 敏感信息处理

- **`config.json` 绝不入库**：它含有本机 `data_root` 绝对路径等机器专属信息，已被 `.gitignore` 永久排除。若你在 PR 中不小心包含它，维护者会拒绝合并并提醒你删除。
- **个人数据外移**：真实的 `categories.md`（供应商 / 人名等）位于 `<DATA_ROOT>/categories.md`，不属于本仓库。仓库内的 `references/categories.md` 仅为通用空模板。
- **不写凭据**：周报 / 日报内容不写入任何账号、密码、token 等敏感凭据。

## 漏洞报告

如发现安全相关问题（而非一般 bug），请**不要公开提 Issue**，改为私信仓库所有者，或在 GitHub 上发起 Security Advisory。

## 供应链

- 脚本仅依赖 Python 标准库 + 少量受管依赖，无第三方网络调用。
- 安装请从官方仓库 `https://github.com/fyuuwang/work-log` 获取，避免使用来源不明的 fork。
