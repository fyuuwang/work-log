# work-log

> 工作日志与 WorkBuddy credit 用量追踪助手。每天/每周自动沉淀工作内容与用量，生成给自己看的大/小两层总结与给领导的周报。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

改编自 Matt Pocock 的 `teach` / `to-issues` 一类 skill 思路，为其注入「央企 IT 项目管理」的工作流：待办 pipeline、每日晨报/回顾、周五自阅周报 + 领导周报、以及 credit 用量日结。

---

## 一、它解决什么

- **待办有归口**：`todo.md`（人读）+ `todos.json`（机读）双轨，按父任务分类、P1/P2/P3 优先级、✅/timebox/pending 三态、7 天自动归档。
- **每日不丢活**：晨间 09:15 生成待办晨报；每日 17:00 回顾并补登已完成项。
- **周报自动出**：周五 17:20 生成两份周报——③自阅（求全、三要素点名给自己看）、④领导（求简、通用化去名给领导看）。
- **用量可追踪**：读取 WorkBuddy 实时 credit 消耗，日结进 `usage/daily_usage.md`。

---

## 二、目录结构

```
work-log/
├── SKILL.md                 # skill 入口与总调度
├── PIPELINE.md              # 三自动化编排与数据流说明
├── config.template.json     # 配置模板（复制为 config.json 后填写）
├── .gitignore               # 已排除 config.json（本机专属）
├── references/
│   ├── categories.md        # 通用空模板（个人真实分类表外移到 <DATA_ROOT>）
│   ├── db-schema.md         # 待办/周报的数据结构
│   ├── mode-morning.md      # 晨间模式话术
│   ├── mode-daily.md        # 每日回顾模式话术
│   ├── mode-weekly.md       # 周报模式（③自阅 + ④领导 提取管线）
│   ├── mode-setup.md        # 首次配置向导
│   └── usage-tracking.md    # 用量追踪说明
└── scripts/
    ├── read_credits.py      # 读取 credit 用量
    ├── read_trace.py        # 读取会话 trace 用于周报回溯
    └── render_todo.py       # 渲染待办晨报/回顾
```

---

## 三、安装

### 方式一：从 GitHub 安装（WorkBuddy / Cowork / Codex）

给智能体的指令：

```
Install work-log from: https://github.com/fyuuwang/work-log
```

### 方式二：手动克隆

```bash
git clone https://github.com/fyuuwang/work-log.git
cp -r work-log ~/.workbuddy/skills/work-log   # 按你的 skill 目录调整
```

### 首次配置（必须）

本 skill 是 **config-driven**，所有路径用 `<DATA_ROOT>` / `<PYTHON>` 占位，由 `config.json` 提供（**本机专属，已被 .gitignore 排除，不进分享包**）：

```bash
cd ~/.workbuddy/skills/work-log
cp config.template.json config.json
# 编辑 config.json，填入你的 data_root（建议放云盘防丢，如 OneDrive / 公司网盘）与 python_bin
```

字段说明：

| 字段 | 含义 |
|------|------|
| `data_root` | 工作日志数据根目录（待办/日报/周报/用量都放这） |
| `plan_tiers` | 用量阶梯（base / current） |
| `fallback_models` | 主模型不可用时的降级模型 |
| `python_bin` | Python 解释器路径，`auto` 表示自动探测 |

---

## 四、三个自动化（全局 / 用户级）

| 触发 | 时间 | MODE | 说明 |
|------|------|------|------|
| 晨间 | 每天 09:15 | `morning` | 生成当日待办晨报 |
| 每日回顾 | 每天 17:00 | `daily` | 回顾并补登已完成项 |
| 周五周报 | 周五 17:20 | `weekly` | 生成③自阅 + ④领导两份周报（非周五早退） |

> 三个自动化归属**全局（用户级）**，存于 `~/.workbuddy/workbuddy.db`，`cwds` 固定指向 work-log 数据工作区；严禁挂到「工作任务平台」等其他项目。

---

## 五、数据安全

- **`config.json` 不进版本库**：含本机 `data_root` 绝对路径，已加入 `.gitignore`。
- **个人数据已外移**：真实的 `categories.md`（含供应商/人名）放在 `<DATA_ROOT>/categories.md`，仓库内的 `references/categories.md` 是通用空模板，可安全分享。
- **周报三要素点名规则**：自阅周报每条必须点名【具体对象 + 具体动作 + 产出】，但不写入任何敏感凭据。

---

## 六、相关

- 同源另一个公开 skill：[fyuu-tutor](https://github.com/fyuuwang/fyuu-tutor)（基于文档的自适应辅导）

## License

[MIT](LICENSE) © 2026 fyuuwang
