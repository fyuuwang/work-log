# 模式 Setup：首次配置向导（MODE=setup）

> 本文件是**首次使用**的引导 SOP。正常情况 3 个自动化 + 用户手动触发都不走这里；
> 仅在检测到 skill 目录下**缺少 `config.json`**，或用户明确要求"初始化/重配"时执行。
> 目标：生成个人 `config.json` + 在 `<DATA_ROOT>` 建立标准骨架，使 skill 立刻可用且零个人数据硬编码。

---

## 触发条件

- 用户说"初始化 work-log / 配置一下 / 第一次用 / setup"。
- 或运行时发现 `config.json` 不存在（如 `render_todo.py` 报"未解析到数据根"）。

---

## 执行步骤

### 1. 确认数据根（data_root）

询问用户工作日志数据根的绝对路径（建议放云盘防丢，如 OneDrive / 公司网盘）。
若用户无法决定，给一个本机默认建议并让其确认，例如 `D:/MyWork/work-log`。

> 数据根与个人电脑解耦：同事拿到本 skill 后，只需把 `data_root` 指向自己的目录即可复用，
> 无需改动 skill 任何代码或文档。

### 2. 写 config.json（基于 config.template.json）

在 skill 目录生成 `config.json`：

```json
{
  "_comment": "本机专属，不进分享包/备份镜像",
  "data_root": "<第1步确认的绝对路径>",
  "plan_tiers": { "base": 2000, "current": 4000 },
  "fallback_models": ["DeepSeek", "Codex"],
  "python_bin": "auto"
}
```

- `plan_tiers`：用量套餐档位（基础/当前），用于划算度判定；按用户实际账单填。
- `fallback_models`：兜底模型列表（当 WorkBuddy 本交不可用时的替代）。
- `python_bin`：`"auto"`（默认，取最新受管 Python）或显式解释器绝对路径。

### 3. 建立 DATA_ROOT 标准骨架

在 `<DATA_ROOT>` 下确保以下结构（`mkdir -p` 创建缺失目录）：

```
<DATA_ROOT>/
  todos.json            # {"items":[]}（20 字段待办真相源，空起步）
  archive.json          # {"items":[]}
  morning.md            # 空文件（晨报由脚本覆盖）
  daily/               # 目录（每日总结）
  weekly-self/         # 目录（自阅周报）
  weekly-lead/         # 目录（领导周报）
  usage/               # 目录（用量日结）
  state/last_run.json  # {"last_processed_ms":0,"processed_ids":[]}
  categories.md        # 复制本 skill 的 references/categories.md 模板过去，供 AI 后续自学填充
  style-samples.md     # 可选：用户提供的领导周报文风样本（留空头部即可，无则跳过）
```

> `categories.md` 复制到数据根后，AI 摄取待办会自动学习并填充用户的父任务别名表；
> skill 内的 `references/categories.md` 仅作通用模板，不含任何个人项目。

### 4. 校验

运行一次晨报渲染，确认 `data_root` 解析正确、骨架可用：

```
<PYTHON> ~/.workbuddy/skills/work-log/scripts/render_todo.py render
```

应正常输出 `morning.md` 内容（空待办时显示"无"）。若报"未解析到数据根"，回看第 2 步 config.json 路径。

### 5. 收尾提示

告知用户：
- skill 已就绪；晨间（09:15）/ 每日回顾（17:00）自动化将自动运作。
- 周五周报（17:20）会在周五自动产出 ③ 自阅 + ④ 领导两份。
- 待办摄取：随时说"加待办 / XX做完了"即可；人名/项目会自动归类进 `todos.json` 与 `categories.md`。

---

## 纪律

- `config.json` 是**本机专属**，已被 `.gitignore` 排除，绝不提交到分享仓库/备份镜像。
- 不把用户的真实项目名、人名写进 skill 目录（`references/` 只保留通用模板）。
- 若用户重配（换电脑/换数据根），只需改 `config.json` 的 `data_root`，骨架可整体迁移。
