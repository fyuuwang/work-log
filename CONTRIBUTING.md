# Contributing

本仓库是个人维护的 WorkBuddy skill，欢迎通过 Issue / PR 提建议，但主要由 fyuuwang 维护。

## 本地开发

```bash
git clone https://github.com/fyuuwang/work-log.git
cd work-log
cp config.template.json config.json   # 填入你自己的 data_root / python_bin
```

## 提交规范

- `feat:` 新功能　`fix:` 修复　`docs:` 文档　`chore:` 杂项
- 保持 `config.json` **不进版本库**（已被 `.gitignore` 排除）。任何含本机绝对路径的改动请走 `config.template.json`。
- 个人真实数据（如 `categories.md` 里的供应商/人名）放在 `<DATA_ROOT>`，不要写回 `references/` 模板。

## 分享包

需要把 skill 发给同事时，用仓库根 excluding `config.json` 的快照（即 `git archive` 或分享 zip），而非包含个人 `config.json` 的工作副本。
