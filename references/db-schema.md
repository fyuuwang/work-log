# WorkBuddy 本地数据库结构（用量追踪用）

数据源：`~/.workbuddy/workbuddy.db`（SQLite）。读取用受管 Python：
`~/.workbuddy/binaries/python/versions/3.13.12/python.exe`

> 重要：credit 真实来源是 `session_usage.credit_json`，**不是** `traces/` 目录。
> `traces/` 里没有 credit 字段，`totalTokens` 恒为 0。

## 1. sessions 表（每个对话一行）

| 列 | 类型 | 说明 |
|----|------|------|
| id | TEXT | 会话 UUID |
| title | TEXT | 会话标题（用户输入的第一条消息片段，可能为空/无标题） |
| custom_title | TEXT | **用户手动设置的标题**（如"每日晨间待办 · work-log"），比 title 更准确 |
| model | TEXT | 模型：`hy3` / `auto` / `glm-5.2` / `custom-local:deepseek-v4-flash` 等 |
| mode | TEXT | craft / plan |
| status | TEXT | working / completed / archived / Pending |
| created_at | INTEGER | UTC 毫秒 |
| updated_at | INTEGER | UTC 毫秒 |
| last_activity_at | INTEGER | 最后活动时间 |
| cwd | TEXT | 会话工作目录（可区分项目） |
| project_id | TEXT | 项目 ID |
| user_id | TEXT | 用户 UUID |
| expert_id / expert_locale / expert_marketplace / expert_runtime_identity | TEXT | 专家信息 |
| permission_mode | TEXT | fullAccess / plan / bypassPermissions |
| source_mode | TEXT | working 等 |
| is_playground | INTEGER | 是否为临时/Playground 会话 |
| is_background_automation | INTEGER | 是否为后台自动化（1=是, 0/null=否） |
| deleted_at | INTEGER | 删除时间戳（可为 null） |
| use_sandbox_cli | INTEGER | 是否使用沙箱 CLI |

## 2. session_usage 表（用量一行）

| 列 | 类型 | 说明 |
|----|------|------|
| session_id | TEXT | 关联 sessions.id |
| used | INTEGER | 疑似字节数（非 credit） |
| size | INTEGER | 上下文窗口大小 |
| credit_json | TEXT | JSON: `{"request_id": 12.38}`，一个会话可能多条请求累加 |
| updated_at | INTEGER | UTC 毫秒（credit 记录时间） |

- `credit_json` 为 NULL → 该会话未计费（如 hy3 免费期）。
- 计费会话：`credit_json` 非空，值为各请求 credit 之和。

## 3. credit_json 示例

```json
{"a3a7e4a8e25c441a9003ba62c18d6530": 12.38}
{"64065205d85c4f55a3a14cdca1d14023": 16.92}
```

求和即为该会话消耗 credit。

## 4. 查询示例（read_credits.py 核心 JOIN）

```sql
SELECT s.id, s.title, s.model, s.status,
       su.credit_json,
       COALESCE(su.updated_at, s.updated_at) AS eff_updated
FROM sessions s
LEFT JOIN session_usage su ON s.id = su.session_id
WHERE COALESCE(su.updated_at, s.updated_at) BETWEEN ? AND ?
ORDER BY eff_updated ASC;
```

## 5. 时区说明

`updated_at` / `created_at` 均为 **UTC 毫秒**。按"本地日期"过滤时，务必把本地日期
换算成 UTC 区间（本机 GMT+8，差 8 小时），否则傍晚的会话会被算到前一天。
`read_credits.py` 已处理该换算。

## 6. 注意事项

## 7. Traces 目录（会话内容数据源）

除了 DB，`~/.workbuddy/traces/` 目录（目前 547 个 JSON 文件）存储了**每次 AI 回复的完整记录**，包括：

| 字段 | 类型 | 说明 |
|------|------|------|
| trace.sessionId | TEXT | 会话 UUID，可 JOIN sessions 表 |
| trace.startedAt | TEXT | ISO 8601 时间戳 |
| trace.modelInfo | OBJECT | 模型名称 |
| spans[].toolInput | TEXT | 完整会话历史（含 system prompt + 所有 user/assistant 消息），可通过 `<user_query>` 标签提取用户提问 |
| spans[].toolOutput | TEXT | AI 回答内容 |

- trace 文件按子目录分组（181 个目录），查询时需全量扫描匹配 sessionId 或日期。
- 用于 `read_trace.py` 脚本提取会话上下文摘要，弥补 DB 中无对话内容的缺口。

- hy3 是否免费以 `credit_json` 是否为 NULL 为准，不以模型名判断（曾有 hy3 会话产生
  credit 的实例）。
- 不要手填 credit 数字，全部由 `read_credits.py` 从数据库读出。
- 不要估算"省了多少 DeepSeek Token"——不可比，禁止写入用量记录。
