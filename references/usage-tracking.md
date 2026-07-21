# 用量日结标准章节（修正版）

> 本文件替换原"用量日结 Prompt"中**有 3 个致命错误**的版本。修正点：
> ① 不再引用不存在的 `read_credits.py`——本 skill 已自带真实脚本；
> ② 数据源从 `traces/` 改为 `~/.workbuddy/workbuddy.db` 的 `session_usage.credit_json`；
> ③ 删除虚构的模型倍率表（deepseek-v4-flash=x0.13 等），直接读 `credit_json` 实值。

## 数据来源（唯一可信源）

调用脚本读取本地数据库：

```
<PYTHON> ~/.workbuddy/skills/work-log/scripts/read_credits.py --date <今天>
```

输出：每会话 `model | credit | (free)`，加当日合计与模型分布。
credit 数字**机器读，不手填**；类型/模型/结果从数据库与会话推断，推断不到写"无法读取"。

## 每日追加内容（写入 `<DATA_ROOT>/usage/daily_usage.md`（APPEND ONLY）

1. **日期**
2. **任务清单**（每行）：`类型 | 模型 | 积分 | 结果 | 若不用WorkBuddy本交（见 config.fallback_models）`
   - 类型/模型/积分/结果：取脚本输出 + 当天会话推断；推断不到写"无法读取"
   - 结果填：一次完成 / 返工后完成 / 失败兜底
   - **若不用WorkBuddy本交**（见 config.fallback_models；不会用同样由用户口述）：**只有用户能判断，由用户口述补充**
3. **今日消耗积分**：取脚本输出（hy3 免费期显示 free 属正常）
4. **今日返工 / 模型切换 / 失败次数**：从会话推断，否则标"无法读取"
5. **今日价值评价**（四选一）：明显省 API+时间 / 主要省时间 / 持平 / 成本或返工过高
6. **滚动指标**（读该文件累计计算）：
   - 累计已用积分、累计成功任务数
   - 平均每个成功任务消耗积分
   - 按当前速度推算本月所需积分
   - 基础积分（config.plan_tiers.base）是否够用、当前积分（config.plan_tiers.current）是否够用
7. **一句结论**：建议保留 / 继续观察 / 不建议续费标准版

## 纪律

- 只用真实数据；读不到的写"无法读取"
- **不要估算"省了多少兜底模型 Token"**（不可比，禁止写入）
- 每天小节控制在 500 字内

## 判定口径（连续 5–10 天后看）

- 当前积分（config.plan_tiers.current）按当前速度能覆盖整月，且失败/兜底率低 → **可保留**
- 频繁需回 config.fallback_models 兜底，或预测积分明显超 config.plan_tiers.current → **标准版未形成稳定替代价值**

## 备注

- 当前（2026-07）hy3 多数会话 `credit_json` 为 NULL（免费）；若出现 hy3 会话带 credit 值，
  以数据库实值为准，照实记录。
- "config.plan_tiers.base 基础 / config.plan_tiers.current 当前"为套餐额度，由用户按实际账单确认，脚本不预设。
