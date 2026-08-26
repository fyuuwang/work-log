# 待办 Pipeline 主规范（work-log · 待办模块）

> 本文件是待办模块的**总契约**。SKILL.md 模式 A 指向此处；`mode-morning.md` 为摄取细则。
> 设计哲学：**机械归脚本，语义归 AI；展示层零 AI 判断。**

---

## 0. 核心原则

1. **数据源是结构化 JSON，不是 Markdown。** `todo.md` 旧式 Markdown 已废弃，待办真相源为 `<DATA_ROOT>/todos.json`。
2. **AI 只做语义层**：听懂人话、整理措辞、按 `categories.md` 归类、把数据写进 `todos.json`、标记完成。AI **绝不**在展示环节重新排版。
3. **脚本只做机械层**：解析 JSON → 渲染晨报 / 计数 / 按日期归档 / 按维度统计。脚本是确定性程序，不做语义判断。
4. **晨报 = 脚本生成的 `morning.md`，AI 原样推送**，不做任何格式改写。
5. **摄取是"直接加、事后审"**：AI 把待办写进 JSON 后立刻 `--render` 给你看结果；你事后核对，不对再提，AI 改。不用来回确认才写。

---

## 1. 文件布局

```
skills/work-log/                     # 本 skill 代码（用户级，可分享）
  PIPELINE.md                        # 【本文件】主规范
  SKILL.md                           # 入口，模式A指向 PIPELINE
  config.json                        # 【本机专属】data_root 等，不进分享包
  references/
    categories.md                    # 父任务别名 + type/source 受控词表（AI 归类用，个人自学填充）
    mode-morning.md                  # 摄取细则（加待办/标记完成）
    mode-daily.md                    # 每日回顾
    mode-weekly.md usage-tracking.md db-schema.md mode-setup.md
  scripts/
    render_todo.py                   # 【机械层】render/archive/report/export-csv
    read_credits.py                  # 用量（不变）

<DATA_ROOT>/                         # 运行时数据根（由 config.json 提供）
  todos.json                         # 【真相源】全部待办（20字段）
  archive.json                       # 归档层：done 且 >14天（只增不删）
  morning.md                         # 晨报（脚本每日覆盖）
  report-YYYYMMDD.md / .csv          # 临时统计报表（脚本生成）
  todo.md                            # 已废弃（保留作历史，不再写入）
  daily/ weekly-*/ usage/ state/     # 不变
  categories.md                      # 个人词表（首次由向导生成空白模板，AI 后续自学填充）
```

---

## 2. 数据模型（20 字段）

每条待办是一个 JSON 对象，字段如下（✅必填 / ◻选填）：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 唯一短ID（如 `t001`），稳定标识，支持修改/完成追踪 |
| `title` | ✅ | 待办内容（AI 整理后的简洁条目） |
| `parent` | ✅ | 父任务/项目（group-by 主键；零散任务=`其他`） |
| `subgroup` | ◻ | 二级分组（如"昭津银行账户增加""共享节点调整"），在同 parent 内进一步归类；没有则不填，渲染时自动以粗体子组标题隔开 |
| `type` | ✅ | 受控词表：需求/开发/采购/审批/会议/文档/沟通/其他 |
| `source` | ✅ | 受控词表：领导交办/会议/自查/供应商/其他 |
| `status` | ✅ | `open` / `waiting` / `done` |
| `priority` | ◻ | P1 / P2 / P3 |
| `assignee` | ◻ | 协作人；文字出现人名则 AI 自动抓取填入 |
| `supplier` | ◻ | 外部供应商（如 乙方供应商） |
| `created_date` | ✅ | 添加日期 `YYYY-MM-DD` |
| `updated_date` | ✅ | 最近修改日期（任何编辑刷新） |
| `started_date` | ◻ | 实际开始日 |
| `completed_date` | ◻ | 完成日期；`open`/`waiting` 时为 `null` |
| `due_date` | ◻ | 截止日期 |
| `waiting_for` | ◻ | `status=waiting` 时填，如 `某同事` |
| `reviewed` | ✅ | 是否经你人工核对（`false` 默认，`true` 核对后） |
| `result` | ◻ | 交付物/结论（`done` 时填） |
| `tags` | ◻ | 自由多标签（数组，如 `["合同","紧急"]`） |
| `notes` | ◻ | 备注（单行） |

`todos.json` 结构：`{"items":[ {…}, … ]}`。

---

## 3. 脚本命令（机械层，零判断）

脚本：`scripts/render_todo.py`（纯标准库 `json`/`csv`/`datetime`/`argparse`）。
数据根默认读取 `config.json` 的 `data_root`，可用 `--data` 覆盖。

### 3.1 `render` —— 生成晨报
```
python render_todo.py render [--days 14] [--data DIR] [--out morning.md] [--no-done]
```
- 读取 `todos.json`。
- 进行中分两区：`open` = 「进行中（我要做）」、`waiting` = 「⏳ 等待中（等别人）」；近完成 = `status == done` 且 `completed_date >= 今天-天数`。
- 生成 `morning.md`：标题 + 进度概览（🔴进行中 N ｜ ⏳等待中 M ｜ ✅已完成 K）+ 按 `parent` 分组列出两区（同一 parent 内按 `subgroup` 二级分组；组内按 priority→due→created 排序） + 列出近完成。
- 待提醒区分「⚠️ 已逾期（超 N 天）」置顶与「⏳ 未到期」两节（逾期天数由脚本自动算）。
- `--no-done`：跳过"已完成"节（摄取反馈精简用，见入口 A）。
- 仅渲染，**不归档**（摄取时用）。

### 3.2 `archive` —— 归档超期完成项
```
python render_todo.py archive [--days 14] [--data DIR]
```
- 把 `completed_date < 今天-天数` 的 `done` 项追加进 `archive.json`，并从 `todos.json` 删除。
- **只动 `done` 项，绝不碰 `open`/`waiting`（安全原则）**。
- 归档前对 `todos.json` 拍 `.bak` 快照 → 内存构建新内容 → 临时文件原子改名 → 写后校验；异常放弃并还原快照。
- 无日期的 `done` 项视为最旧，立即归档。

### 3.3 `validate` —— 数据完整性校验（2026-08-26 新增）
```
python render_todo.py validate [--data DIR]
```
- 校验 `todos.json` / `archive.json`：JSON 语法、`items` 结构、必填字段、id 唯一、枚举（status 硬校验；type/source 为 WARN，允许新增词）、日期格式、语义一致性（`waiting_for`↔`status`、`completed_date`↔`done`）、`reviewed`/`tags` 类型。
- 输出 `✓ 校验通过` 或错误/警告清单；**存在 ERROR 时退出码 1**（AI 必须修复后再渲染）。
- **摄取后强制执行**（见入口 A），防 JSON 手改损坏（2026-08-26 t093 逗号事故教训）。

### 3.3 `report` —— 按日期范围 + 维度统计
```
python render_todo.py report --from YYYY-MM-DD --to YYYY-MM-DD \
    --group-by parent|type|source|assignee [--metric completed|created|all] \
    [--format md|csv] [--out FILE]
```
- `--metric completed`：按 `completed_date` 在范围内筛选 `done` 项（默认）。
- `--metric created`：按 `created_date` 在范围内筛选。
- `--metric all`：范围内被"创建或完成"触碰到的项。
- 按 `--group-by` 维度聚合计数（总数 / 已完成数 / 进行中数），输出 Markdown 表或 CSV。
- 默认打印到 stdout（AI 可直接读）；`--out` 落盘。

### 3.4 `export-csv` —— 导出 Excel
```
python render_todo.py export-csv [--out todos.csv]
```
- 把所有 `items` 平铺成 CSV（含全部 20 字段，`tags` 用 `;` 连接），供你在 Excel 自行透视。

---

## 4. 三个入口

### 入口 A：摄取（"把待办加进去"，用户触发）
1. 你说人话（"加个 X；Y。Z 做完了"）。
2. AI 语义层：① 语言调整（口语→简洁条目）② 查 `categories.md` 别名→归 `parent`，从受控词表选 `type`/`source` ③ **人名自动抓**进 `assignee` ④ 写/改 `todos.json`（新增挂到对应 `parent`；"X做完了"→该条 `status=done`、`completed_date=今天`、`updated_date=今天`）⑤ 新项 `reviewed=false`。
3. AI 跑 `render_todo.py validate` **防错校验**：有 `[ERROR]` 先修复再继续（不许带错渲染）；`[WARN]` 顺手修正。
4. AI 跑 `render_todo.py render --no-done`，展示**进行中 / 等待中**两个区块，并**点出"新增 X、Y 落在『父任务』"**供你审核（2026-08-26 起不再贴全量晨报，已完成列表只在晨跑展示）。
5. **你事后核对**：无误不管；有误提异议 → AI 改 `todos.json` 重跑（重跑同样走 validate → render --no-done）。

**跨文件移动细则（"X做完了"）**：
- 在 `todos.json` 按 `id` 或（`parent`+`title` 近似）定位该条 → 置 `status=done`、`completed_date=今天`、`updated_date=今天`；若原 `assignee` 为空且文字有人名则补抓。
- 找不到源行 → **提示你确认**（不臆造新条）。

### 入口 B：晨跑（"每天早上跑一下"，自动化 09:15）
- 自动化 prompt 跑 `render_todo.py render --archive`（先归档超期，再渲染），读取 `morning.md` **原样推送**给你。AI 不重写格式。

### 入口 C：看工作情况（"看某天到某天"，用户触发）
- 你说"看 7/1 到 7/15 各项目完成啥了" → AI 跑 `report --from 2026-07-01 --to 2026-07-15 --group-by parent` 并把结果给你。

---

## 5. 旧逻辑清理（与每日回顾的边界）

| # | 旧问题 | 处理 |
|---|--------|------|
| 1 | `mode-daily.md` 第5节"7天归档"与晨跑14天归档冲突 | **已删** mode-daily 第5节；归档只在晨跑 |
| 2 | 晨间自动化 prompt 写"读文件直接输出" | **已改**为"跑脚本+推 morning.md" |
| 3 | "X做完了"搬家 | 写死为 `todos.json` 内 `status`/`completed_date` 变更（见入口A） |
| 4 | 零散任务落点 | 归入 `parent="其他"` |
| 5 | 新项目识别 | AI 遇 `categories.md` 未覆盖的项目，提议别名，你确认后写入 |
| 6 | 显示一致 | 摄取与晨跑都只显示 ≤14天 `done` |

---

## 6. 安全约定（归档）

- 归档**只移 `done` 项**，`open`/`waiting` 永不被触碰。
- 每次归档前对 `todos.json` 拍 `.bak`；异常整体放弃并还原，绝不半成品写入。
- `archive.json` 只追加，不删历史。

---

## 7. 人名自动抓取规则

- 待办文字出现人名（如"等某同事""找某负责人要材料""让某同事"），AI 把该人名写入 `assignee`。
- 人名识别参考 `categories.md` 的父任务别名表（含人员别名，如 某同事A/某同事B）。
- 系统/工具名（如某平台能力）不强制填 `assignee`，可放 `notes`。
