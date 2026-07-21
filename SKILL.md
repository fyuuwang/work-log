---
name: work-log
agent_created: true
allowed-tools: Read,Bash,Write,conversation_search,WebFetch
description: >
  工作日志与用量追踪助手。每天/每周自动沉淀工作内容与 WorkBuddy credit 用量，
  用于评估标准版套餐是否划算。务必在以下场景使用：用户说"工作日志""日报"
  "周报""每日复盘""今天干了什么""本周干了什么""待办""用量日结""credit 用了多少"
  "workbuddy 花了多少""套餐划算吗"；或自动化以【MODE=morning】产出晨间待办、
  【MODE=daily】做每日回顾+用量、【MODE=weekly】做周五周报时。本 skill 由 3 个
  WorkBuddy 自动化按固定时间调用，也可由用户手动触发对应模式。
---

# Work Log（工作日志 + 用量追踪）

每日/每周自动记录工作内容（大/小两层总结）与 WorkBuddy credit 用量，支撑
"标准版套餐是否划算"的决策。

## 何时使用

- 自动化在固定时间调用（见"模式分发"）。
- 用户手动提到工作日志、日报、周报、待办、用量日结等场景。

## 模式分发

解析触发指令里的模式令牌，跳转到对应章节（详细 SOP 在 `references/`）：

- `【MODE=morning】` → 见下方「模式 A」+ `references/mode-morning.md`
- `【MODE=daily】`   → 见下方「模式 B」+ `references/mode-daily.md`
- `【MODE=weekly】`  → 见下方「模式 C」+ `references/mode-weekly.md`

若指令未带模式令牌但语义明显（如用户说"写今天日报"），按 daily 处理。

## 模式 A：晨间待办（09:15）

- **数据源已重构为结构化 JSON**（`E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/todos.json`，19 字段），主规范见 `PIPELINE.md`。
- 晨报由脚本机械生成：跑 `scripts/render_todo.py render --archive` → 读取 `morning.md` **原样推送**（AI 不重写格式，展示层零判断）。
- 三个入口：① **摄取**（"加待办/XX做完了"→ AI 写 JSON，事后人工审核）② **晨跑**（09:15 自动）③ **看工作情况**（`report` 按日期范围 + 父任务/type/source 统计）。
- 详细主规范：`PIPELINE.md`；摄取细则：`references/mode-morning.md`。

## 模式 B：每日工作回顾（17:00）

1. 抓取当天全部会话（`sessions` 表 + `conversation_search`），覆盖全工作区。
2. 跨天增量：读 `E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/state/last_run.json`，按**动态回溯窗口**（运行时取今天日期/星期：平时1天、周一3天、停用多日按 gap 补齐，上限14天）回看、按 session_id 去重追加，
   更新 `last_run.json`。解决周末/停跑遗漏与 17:00–18:00 空档次日补跑。
3. 两层总结：大总结（自阅，全密度）写入 `E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/daily/YYYY-MM-DD.md`；
   小总结（≤200 字，呈报）同文件。
4. 用量小节：调用下方"用量接口"把结果追加到 `E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/usage/daily_usage.md`。
- 详细 SOP：`references/mode-daily.md`

## 模式 C：每周周报（17:20，仅周五）

- 星期网关：触发时先在线抓星期（见 `references/mode-weekly.md` 第 0 节），非周五自动结束。
- 周五则产出：③ 自阅周报（大总结）写入 `weekly-self/YYYY-Www.md`；④ 领导周报（小总结，对③再压缩）写入 `weekly-lead/YYYY-Www.md`。两文件分离，见 `references/mode-weekly.md`。
- 详细 SOP：`references/mode-weekly.md`

## 用量接口（调用脚本）

credit 数字**机器读，不手填**。运行：

```
~/.workbuddy/binaries/python/versions/3.13.12/python.exe ~/.workbuddy/skills/work-log/scripts/read_credits.py --date <今天>
```

- 数据源：`~/.workbuddy/workbuddy.db` 的 `session_usage.credit_json`（**非** traces 目录）。
- 输出：每会话 `model | credit | (free)` + 当日合计 + 模型分布。
- 追加格式与纪律：见 `references/usage-tracking.md`。
- 数据库结构：见 `references/db-schema.md`。

## 全局铁律

- **真实数据**：只写数据库/会话里能核实的内容；读不到写"无法读取"，不编造、不估算。
- **禁止估算"省了多少 DeepSeek Token"**（不可比）。
- **追加不覆盖**：日志/用量文件 APPEND ONLY，绝不删除历史、不覆盖旧小节。
- **两层总结边界**：小总结 ≤200 字且不得超出大总结信息范围。
- **路径绝对化**：所有读写用绝对路径（数据根 `E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/...`，位于独立 OneDrive 工作区，云备份防丢），不依赖当前工作目录。
- **"若不用 WB 本交"只有用户能判断**：该字段由用户口述补充，AI 不替用户下结论。

## 目录约定

```
~/.workbuddy/skills/work-log/                              # 本 skill 代码（用户级，跨项目）
  PIPELINE.md                                             # 待办 pipeline 主规范
  scripts/render_todo.py                                  # 待办机械层（render/archive/report/export-csv）
  scripts/read_credits.py                                 # 用量读取脚本
  references/                                             # 各模式 SOP + 类别表 + 数据库结构 + 用量模板
E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log/       # 运行时数据根（独立 OneDrive 工作区，云备份）
  todos.json                                              # ① 待办真相源（19 字段，结构化）
  archive.json                                            # ② 归档层（done >14 天，只增不删）
  morning.md                                              # ③ 晨报（脚本每日覆盖）
  todo.md                                                 # （已废弃，历史保留，不再写入）
  daily/YYYY-MM-DD.md                                     # ④ 会话总结（每日，大+小）
  weekly-self/YYYY-Www.md                                 # ⑤ 周五自阅周报（基于 daily 再总结）
  weekly-lead/YYYY-Www.md                                 # ⑥ 领导周报（基于 ⑤ 再压缩，独立成品）
  usage/daily_usage.md                                    # 用量日结（累积）
  state/last_run.json                                     # 跨天增量去重状态
```
