# Changelog

## [1.1.0] - 2026-07-28

- **subgroup 二级分组**：待办数据模型新增可选字段 `subgroup`（20 字段），同一 parent 内可按子专题二级分组。`render_todo.py` 渲染 `morning.md` 时自动识别 subgroup 变化并插入粗体子组标题。
- **用友MDG 待办深化**：按用户实际业务结构拆分为"昭津银行账户增加"（2 项）和"共享节点调整"（5 项）两个子组。
- **待办摄取细则更新**：`mode-morning.md` 新增 subgroup 识别与填充指导。
- 清理已废弃的 `work-log-skill-share.zip`（已被 GitHub 仓库取代）。

## [1.0.0] - 2026-07-21

首个可分享版本（此前已在生产环境运行数周）。

- **完全可移植化**：改为 config-driven，所有路径用 `<DATA_ROOT>` / `<PYTHON>` 占位，由 `config.json` 提供（机器专属，已加入 `.gitignore`）。
- **个人数据外移**：真实 `categories.md`（含供应商/人名）迁至 `<DATA_ROOT>/categories.md`；仓库内 `references/categories.md` 改为通用空模板，可安全分享。
- **周报重构**：③自阅周报改为「第一部分：本周概要 + 第二部分：Trace 回溯」两段式；新增「三要素点名」写作规则（每条必须点名具体对象 + 具体动作 + 产出）。
- **④领导周报提取管线**：从③动态蒸馏，结构铁律为「一、本周工作总结 + 二、下周工作计划」，供应商通用化、去具体名。
- **三自动化落地**：晨间 09:15 / 每日 17:00 / 周五周报 17:20（全局用户级，cwds 固定指向 work-log 数据工作区）。
- 新增脚本 `render_todo.py`、`read_trace.py`，与既有 `read_credits.py` 构成完整工具链。
- 新增 `config.template.json` + `mode-setup.md` 首次配置向导。

## [0.0.0] - 2026-07-14

内部起点：work-log skill 初版构建（SKILL.md + 5 references + read_credits.py）。
