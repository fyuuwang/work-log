# Changelog

## [1.2.0] - 2026-08-26

- **`validate` 子命令（防错）**：`render_todo.py` 新增数据完整性校验（JSON 语法 / 必填字段 / id 唯一 / 枚举 / 日期格式 / 语义一致性），有 ERROR 退出码 1。摄取后强制运行，防 JSON 手改损坏（2026-08-26 t093 逗号事故教训）。
- **晨报展示层重构**：
  - 「进行中」分两区：`open` = 进行中（我要做）在前、`waiting` = ⏳ 等待中（等别人）后置独立区；进度概览三栏（🔴/⏳/✅）。
  - 组内排序：priority（P1→P3）→ due 升序 → created 升序。
  - `assignee` 与 `waiting_for` 相同时只显示一处（修 "（@香香；等香香）" 重复）。
  - 待提醒区分「⚠️ 已逾期（超 N 天）」置顶 +「⏳ 未到期」，逾期天数脚本自动算。
- **摄取反馈精简**（用户确认）：摄取后只给变更摘要（`render --no-done` + 进行中/等待中区块），不再贴全量晨报；已完成列表只在晨跑展示。
- **daily 防覆盖第二口子**：`mode-daily.md` 落盘前强制检查 `.workbuddy/memory/YYYY-MM-DD.md` 用户手写内容并合并标注（08-20 事故教训）。
- **daily 用量职责边界**：大/小总结只写当日净增；滚动指标唯一出处为 `usage/daily_usage.md`。
- **领导周报软约束**：下周计划同一短标题板块 ≤2 条（合并同类/取关键一条）。
- 数据修正：t066 语义不一致（waiting_for 非空但 status=open）→ 改 waiting。

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
