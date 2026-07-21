#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_credits.py — 读取 WorkBuddy 本地 credit 用量。

数据来源（已实测确认）：
  ~/.workbuddy/workbuddy.db
    - sessions 表: id, title, model(hy3|auto|glm-5.2), status, created_at, updated_at
    - session_usage 表: session_id, credit_json(TEXT, JSON: {"req_id": 12.38}),
                         updated_at(UTC 毫秒)

注意：
  - credit 真实来源是 session_usage.credit_json，NOT traces 目录。
  - hy3 当前免费，credit_json 为 NULL -> 记为 free/0。
  - 数据库 updated_at 存 UTC 毫秒；本脚本按"用户本地日期"换算 UTC 区间，
    避免跨时区把傍晚会话算到前一天。

用法：
  python read_credits.py --date 2026-07-13
  python read_credits.py --since 2026-07-11 --until 2026-07-13
  python read_credits.py --date 2026-07-13 --format json
  python read_credits.py            # 默认最近 3 天
"""
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.expanduser(r"~\.workbuddy\workbuddy.db")


def local_tz():
    """返回本机时区（用于把本地日期正确换算成 UTC 毫秒）。"""
    return datetime.now().astimezone().tzinfo


def to_utc_ms(date_str, end_of_day=False):
    """把 'YYYY-MM-DD' 或 'YYYY-MM-DDTHH:MM:SS' 转成 UTC 毫秒。"""
    s = date_str.strip()
    if "T" in s:
        dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    else:
        dt = datetime.strptime(s, "%Y-%m-%d")
        dt = dt.replace(hour=23, minute=59, second=59) if end_of_day else dt.replace(hour=0, minute=0, second=0)
    dt = dt.replace(tzinfo=local_tz())
    return int(dt.timestamp() * 1000)


def parse_credit_json(raw):
    """返回 (credit数值, is_free)。NULL/空 -> (0.0, True)。"""
    if not raw:
        return 0.0, True
    try:
        d = json.loads(raw)
        if not isinstance(d, dict) or not d:
            return 0.0, True
        return float(sum(d.values())), False
    except Exception:
        return 0.0, True


def main():
    ap = argparse.ArgumentParser(description="Read WorkBuddy credit usage from local db")
    ap.add_argument("--date", help="单日，如 2026-07-13（本地日期）")
    ap.add_argument("--since", help="起始日，如 2026-07-11")
    ap.add_argument("--until", help="结束日，如 2026-07-13")
    ap.add_argument("--format", default="text", choices=["text", "json"])
    args = ap.parse_args()

    # 确定区间（本地日期 -> UTC 毫秒）
    if args.date:
        since_ms = to_utc_ms(args.date, end_of_day=False)
        until_ms = to_utc_ms(args.date, end_of_day=True)
        range_label = args.date
    else:
        since = args.since or (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        until = args.until or datetime.now().strftime("%Y-%m-%d")
        since_ms = to_utc_ms(since, end_of_day=False)
        until_ms = to_utc_ms(until, end_of_day=True)
        range_label = f"{since} ~ {until}"

    if not os.path.exists(DB_PATH):
        print(f"ERROR: 找不到数据库 {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id            AS id,
               s.title         AS title,
               s.model         AS model,
               s.status        AS status,
               su.credit_json  AS credit_json,
               COALESCE(su.updated_at, s.updated_at) AS eff_updated
        FROM sessions s
        LEFT JOIN session_usage su ON s.id = su.session_id
        WHERE COALESCE(su.updated_at, s.updated_at) BETWEEN ? AND ?
        ORDER BY eff_updated ASC
    """, (since_ms, until_ms))
    rows = cur.fetchall()
    conn.close()

    sessions = []
    total_credit = 0.0
    billed = 0
    free = 0
    model_dist = {}
    for r in rows:
        credit, is_free = parse_credit_json(r["credit_json"])
        if is_free:
            free += 1
        else:
            billed += 1
            total_credit += credit
        model_dist[r["model"]] = model_dist.get(r["model"], 0.0) + credit
        sessions.append({
            "id": r["id"],
            "title": r["title"] or "(无标题)",
            "model": r["model"] or "unknown",
            "credit": round(credit, 2),
            "free": is_free,
            "status": r["status"],
            "updated_at": r["eff_updated"],
        })

    if args.format == "json":
        out = {
            "range": range_label,
            "total_credit": round(total_credit, 2),
            "billed_sessions": billed,
            "free_sessions": free,
            "model_distribution": {k: round(v, 2) for k, v in model_dist.items()},
            "sessions": sessions,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"[{range_label}] credit 汇总")
        if not sessions:
            print("  （该区间无会话/用量记录）")
        for s in sessions:
            tag = "free" if s["free"] else f"{s['credit']}"
            print(f"  会话: {s['title']} | model={s['model']} | credit={tag}")
        print(f"  合计: {round(total_credit, 2)} | 计费会话: {billed} | 免费会话: {free}")
        if model_dist:
            print("  模型分布: " + ", ".join(f"{k}={round(v, 2)}" for k, v in model_dist.items()))


if __name__ == "__main__":
    main()
