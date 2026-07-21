# 模式 A 摄取细则（MODE=morning · 加待办 / 标记完成）

> 本文件是"入口 A：摄取"的操作细则。晨报渲染、归档、统计由 `scripts/render_todo.py` 机械完成（见 `PIPELINE.md`）。
> 核心：AI 只做语义（听懂话、归类、写 JSON），展示层零判断。

---

## 触发

- 用户手动说"加待办 / 新增 / XX做完了 / 把 XX 记一下"等。
- 晨间自动化（09:15）走的是 `render_todo.py render --archive` + 推送 `morning.md`，**不**走本摄取流程（除非用户在自动化消息里追加待办）。

---

## 数据源

`<DATA_ROOT>/todos.json`（19 字段，见 `PIPELINE.md` 第 2 节）。
类别映射参考 `references/categories.md`（父任务别名 + type/source 受控词表）。

---

## 摄取流程（"把待办加进去"）

1. **解析用户的话**：拆成若干条目（如"加 X；Y。Z 做完了"→ X、Y 新增，Z 标记完成）。
2. **语言调整**：口语 → 简洁条目（保留关键信息，去掉口水话）。
3. **分类映射**（查 `categories.md`）：
   - 父任务 `parent`：按别名表归并（如"某同事A""某同事B"→ 对应 `父任务`）。
   - `type` / `source`：从受控词表选最贴切的值。
   - 未命中且明显是新项目 → **提议**新父任务/新词，待用户确认后写入 `categories.md`（不擅自创造规范值）。
4. **人名自动抓**：条目文字出现人名（如"等某同事""找某负责人要材料""让某同事"）→ 写入 `assignee`。
5. **写/改 `todos.json`**：
   - 新增：追加一条，`id` 取当前最大序号+1（如 `t010`），`created_date`=`updated_date`=今天，`reviewed`=false，`status` 推断（open / waiting 若有"等X"）。
   - "X做完了"：定位该条（按 `id` 或 `parent`+`title` 近似）→ 置 `status=done`、`completed_date`=今天、`updated_date`=今天；若 `assignee` 空且文字有人名则补抓。**找不到源行 → 提示用户确认，不臆造。**
6. **立刻 `--render`** 生成 `morning.md`，把内容给用户看，并**点出"新增 X、Y 落在『父任务』"**供审核。
7. **人工审核闭环**：用户事后核对；无误不管；有误提异议 → AI 改 `todos.json` 重跑。不用来回确认才写。

---

## 纪律

- 不在展示环节重新排版；晨报 = 脚本生成的 `morning.md`，原样推送。
- 不编造待办；用户没说的字段（如 `result`）不臆测填充。
- `reviewed` 默认 false，待用户核对后置 true（报表可筛"未审"）。
- 选填字段（`due_date`/`assignee`/`result` 等）没有就不写。
