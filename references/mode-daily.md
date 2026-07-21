# 模式 B：每日工作回顾（MODE=daily）

触发：自动化 B，每天 17:00。
目标：回顾当天全部工作会话，产出大/小总结，并完成跨天增量补跑与用量追踪。

> 路径中的 `<DATA_ROOT>` 指 `config.json` 的 `data_root`；`<PYTHON>` 指按 `python_bin` 解析的 Python 解释器。

## 1. 抓取当天全部会话

- 主源：`~/.workbuddy/workbuddy.db` 的 `sessions` 表，按 `created_at`/`updated_at` 过滤当天（本地日期，注意 UTC 换算）。
- 覆盖全部工作区（sessions 是全局的），不限于单一 workspace。

## 2. 从 traces 提取会话原始上下文

- 从 .1 步获取当天所有 session_id，对每个 session_id 运行脚本提取 trace 摘要：

  ```
  <PYTHON> ~/.workbuddy/skills/work-log/scripts/read_trace.py --session <session_id>
  ```

- 输出为 JSON：每个会话的交互轮次，含 `user_asked`（用户原始提问）和 `ai_key_output`（AI 回答摘要）。
- 此上下文是"大总结"的主要素材来源：**不再仅凭会话标题推断内容**，而是从 trace 中的实际对话提取具体做了什么、涉及什么系统/文件、产出了什么决策。
- 如果 `--session` 模式无返回，尝试 `--date <今天>` 全量扫描回退。
- **成本说明**：每个 trace 文件仅读取少量关键字段（user_query + AI 回复摘要），不读取完整系统提示词或来回历史，平均每个会话约 1-2KB input token，费用在 0.01-0.05 credit/会话级。
- 保留 `conversation_search` 作为辅助（如有返回则可用于补充）。

## 3. 跨天增量补跑（动态回溯窗口，解决周末/停跑遗漏）

- 读取 `<DATA_ROOT>/state/last_run.json`（不存在则视为首次）。
- **运行时先取今天日期与星期**（执行 `date` 命令，不要依赖模型记忆）：
  ```
  date +%Y-%m-%d        # 今天
  date +%u              # 星期 1=周一 … 7=周日
  ```
- **动态回溯天数 `LOOKBACK`** 按下列规则计算（按天取整，UTC 已换算本地）：
  - `gap` =（今天 − `last_run.last_processed_ms` 对应日期）的天数；首次运行取 `gap=14`。
  - 星期基准 `base`：周一 `base=3`（覆盖周五+周末）/ 其余 `base=1`。
  - `LOOKBACK = min( max(base, gap), 14 )`。
  - 即：平时回看 1 天；周一回看 3 天；若停用多日则按 `gap` 补齐（上限 14 天防失控）。
- 按 `session_id` 去重：只处理 `last_run.json` 中 `processed_ids` 未包含的会话，追加增量，不重复已写内容。
- 处理完更新 `<DATA_ROOT>/state/last_run.json`：`last_processed_ms` = 现在，`processed_ids` = 旧值 ∪ 本次所有涉及 session_id（**累积并集**去重，绝不覆盖旧值；这样任意会话只会被处理一次）。
- **成本说明**：窗口放宽不显著增加耗时——`sessions` 表按时间戳过滤是廉价 SQL；真正逐会话处理只发生在 `processed_ids` 未包含的新会话上，已处理会话被去重瞬间跳过。因此 7/14 天窗口在首次补齐后，日常运行几乎只处理 0~数条新会话。

`last_run.json` 结构：
```json
{ "last_processed_ms": 1783869731628, "processed_ids": ["id1", "id2"] }
```

## 4. 两层总结（铁律）

- **大总结**（给自己）：逐会话全量自阅，尽量保留原始密度与关键决策/产出。
  写入 `<DATA_ROOT>/daily/YYYY-MM-DD.md` 的"大总结"节。
- **小总结**（给领导）：≤200 字，只列干了什么 + 关键产出，禁止编造大总结之外的信息。
  写入同文件"小总结"节。

## 5. 用量小节（调用脚本，追加独立文件）

运行：
```
<PYTHON> ~/.workbuddy/skills/work-log/scripts/read_credits.py --date <今天>
```
按 `references/usage-tracking.md` 的"每日追加内容"格式，把结果**追加**到
`<DATA_ROOT>/usage/daily_usage.md`（APPEND ONLY，不覆盖）。

## 6. 落盘

- 工作日志：`<DATA_ROOT>/daily/YYYY-MM-DD.md`（不存在则新建，存在则追加当天小节；写前先 `mkdir -p` 确保 `daily/` 存在）。
- 用量：`<DATA_ROOT>/usage/daily_usage.md`（独立文件）。

## 输出格式（日志文件内）

```
# YYYY-MM-DD 工作日志

## 大总结（自阅）
- <会话1>：做了什么、关键决策、产出
- <会话2>：...

## 小总结（呈报）
今日完成 X 项：<一句话列要点>。

## 用量日结
（见 usage/daily_usage.md，本模式已追加）
```

## 纪律

- 只读约束不适用本模式（需要写日志/用量文件）。但禁止删除历史、禁止覆盖旧小节。
- 真实数据，不估算，不编造。
- 大总结求全，小总结求简；小总结不得超出大总结信息范围。
