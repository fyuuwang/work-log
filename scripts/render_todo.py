#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_todo.py —— work-log 待办机械层（纯标准库，零依赖）

子命令：
  render      生成晨报 morning.md（不归档）
  archive     把 >N 天的 done 项移入 archive.json（只动 done，安全）
  report      按日期范围 + 维度统计（parent/type/source/assignee）
  export-csv  导出全部待办为 CSV（供 Excel 透视）

设计原则：机械、确定性、零语义判断。展示层格式由本脚本统一产出，AI 不二次加工。
"""
import argparse
import csv
import json
import os
import shutil
from datetime import date, datetime, timedelta

# ---- 默认路径（数据根，可用 --data 覆盖）----
DEFAULT_DATA_DIR = r"E:/OneDrive/Datas/03_中旅发展/AI_WorkPlace/work-log"
TODO_FILE = "todos.json"
ARCHIVE_FILE = "archive.json"
MORNING_FILE = "morning.md"
DEFAULT_DAYS = 14

CN = "一二三四五六七八九十"


def cn_num(n):
    if 1 <= n <= 10:
        return CN[n - 1]
    return str(n)


def d(s):
    """解析 YYYY-MM-DD -> date，非法/空返回 None"""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def today():
    return date.today()


def load(path):
    if not os.path.exists(path):
        return {"items": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def backup_and_save(path, data):
    """写前拍 .bak 快照 -> 临时文件原子改名 -> 写后校验；异常放弃（原文件不动）。"""
    bak = path + ".bak"
    if os.path.exists(path):
        shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 校验写出的 JSON 可解析
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)
    os.replace(tmp, path)


def fmt_item(it):
    """渲染单条进行中项的正文（不含前缀 - [ ]）。"""
    s = ""
    if it.get("priority"):
        s += f"({it['priority']}) "
    s += it.get("title", "")
    extra = []
    if it.get("assignee"):
        extra.append(f"@{it['assignee']}")
    if it.get("status") == "waiting" and it.get("waiting_for"):
        extra.append(f"等{it['waiting_for']}")
    if it.get("due_date"):
        extra.append(f"截止{it['due_date']}")
    if extra:
        s += " （" + "；".join(extra) + "）"
    return s


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def render(data_dir, days, out_name=MORNING_FILE):
    todo_path = os.path.join(data_dir, TODO_FILE)
    data = load(todo_path)
    items = data.get("items", [])
    t = today()
    cutoff = t - timedelta(days=days)

    open_items = [i for i in items if i.get("status") != "done"]
    recent_done = [
        i for i in items
        if i.get("status") == "done" and (d(i.get("completed_date")) or t) >= cutoff
    ]

    # 按 parent 分组（保持首次出现顺序）
    groups = []
    gmap = {}
    for it in open_items:
        p = it.get("parent") or "其他"
        if p not in gmap:
            gmap[p] = []
            groups.append(p)
        gmap[p].append(it)

    lines = []
    lines.append(f"# 晨间待办 · {t.isoformat()}")
    lines.append("")
    lines.append(f"**进度概览**：🔴 进行中 {len(open_items)} 项 ｜ ✅ 已完成 {len(recent_done)} 项")
    lines.append("")
    lines.append("## 进行中（未完成优先）")
    if not open_items:
        lines.append("_无_")
    else:
        for idx, p in enumerate(groups, 1):
            lines.append(f"### {cn_num(idx)}、{p}")
            for it in gmap[p]:
                lines.append("  - [ ] " + fmt_item(it))
    lines.append("")
    lines.append(f"## 已完成（近 {days} 天）")
    if not recent_done:
        lines.append("_无_")
    else:
        for it in sorted(recent_done, key=lambda x: d(x.get("completed_date")) or t, reverse=True):
            cd = it.get("completed_date") or ""
            parent = it.get("parent") or "其他"
            line = f"✅ {it.get('title', '')} - {parent}"
            suffix = []
            if cd:
                suffix.append(cd)
            if it.get("result"):
                suffix.append(it["result"])
            if suffix:
                line += " （" + "，".join(suffix) + "）"
            lines.append(line)
    lines.append("")

    # 待提醒：进行中且设了 due_date 的项，按截止日升序突出（用于"下周一着重提醒"等）
    remind = [i for i in open_items if i.get("due_date")]
    if remind:
        remind.sort(key=lambda x: d(x.get("due_date")) or t)
        lines.append("## ⏰ 待提醒（设了截止日）")
        for it in remind:
            due = it.get("due_date") or ""
            parent = it.get("parent") or "其他"
            line = f"  ⏰ {due} ｜ - [ ] {it.get('title', '')} - {parent}"
            extra = []
            if it.get("assignee"):
                extra.append("@" + it["assignee"])
            if it.get("supplier"):
                extra.append("供应商:" + it["supplier"])
            if extra:
                line += " （" + "；".join(extra) + "）"
            lines.append(line)
        lines.append("")

    content = "\n".join(lines)
    out_path = os.path.join(data_dir, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return content


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------
def archive(data_dir, days):
    todo_path = os.path.join(data_dir, TODO_FILE)
    arch_path = os.path.join(data_dir, ARCHIVE_FILE)
    data = load(todo_path)
    items = data.get("items", [])
    t = today()
    cutoff = t - timedelta(days=days)

    to_archive = []
    remain = []
    for it in items:
        if it.get("status") == "done":
            cd = d(it.get("completed_date"))
            if cd is None or cd < cutoff:  # 无日期视为最旧
                to_archive.append(it)
                continue
        remain.append(it)

    if not to_archive:
        return 0

    # 只改 todos.json（open/waiting 永不被触碰）；归档前拍快照+原子写
    backup_and_save(todo_path, {"items": remain})
    arch = load(arch_path)
    arch.setdefault("items", [])
    arch["items"].extend(to_archive)
    backup_and_save(arch_path, arch)
    return len(to_archive)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
FIELDS = ["id", "title", "parent", "type", "source", "status", "priority",
          "assignee", "supplier", "created_date", "updated_date", "started_date",
          "completed_date", "due_date", "waiting_for", "reviewed", "result",
          "tags", "notes"]


def report(data_dir, from_s, to_s, group_by, metric, fmt):
    data = load(os.path.join(data_dir, TODO_FILE))
    items = data.get("items", [])
    f0 = d(from_s)
    t1 = d(to_s)
    if not f0 or not t1:
        raise SystemExit("--from / --to 必须是 YYYY-MM-DD")

    def in_range(it):
        if metric == "completed":
            cd = d(it.get("completed_date"))
            return it.get("status") == "done" and cd and f0 <= cd <= t1
        elif metric == "created":
            cd = d(it.get("created_date"))
            return cd and f0 <= cd <= t1
        else:  # all
            cd = d(it.get("completed_date")) or d(it.get("created_date"))
            return cd and f0 <= cd <= t1

    sel = [it for it in items if in_range(it)]

    groups = {}
    order = []
    for it in sel:
        key = it.get(group_by) or "（未填）"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(it)

    rows = []
    for key in order:
        g = groups[key]
        total = len(g)
        done = sum(1 for x in g if x.get("status") == "done")
        rows.append((key, total, done, total - done))

    if fmt == "csv":
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["分组", "总数", "已完成", "进行中"])
        for key, total, done, openc in rows:
            w.writerow([key, total, done, openc])
        return buf.getvalue()
    else:
        lines = []
        lines.append(f"# 工作情况报表 · {from_s} ~ {to_s}")
        lines.append("")
        lines.append(f"维度：`{group_by}` ｜ 指标：`{metric}` ｜ 命中 **{len(sel)}** 项")
        lines.append("")
        lines.append("| 分组 | 总数 | 已完成 | 进行中 |")
        lines.append("|------|------|--------|--------|")
        for key, total, done, openc in rows:
            lines.append(f"| {key} | {total} | {done} | {openc} |")
        lines.append("")
        lines.append("## 明细")
        for key in order:
            lines.append(f"### {key}")
            for it in groups[key]:
                dt = it.get("completed_date") or it.get("created_date") or ""
                lines.append(f"- {it.get('title', '')} （{dt}）")
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# export-csv
# ---------------------------------------------------------------------------
def export_csv(data_dir, out_name):
    data = load(os.path.join(data_dir, TODO_FILE))
    items = data.get("items", [])
    out = os.path.join(data_dir, out_name)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for it in items:
            row = []
            for fld in FIELDS:
                v = it.get(fld, "")
                if fld == "tags" and isinstance(v, list):
                    v = ";".join(v)
                row.append(v if v != "" else "")
            w.writerow(row)
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="work-log 待办机械层")
    sub = parser.add_subparsers(dest="cmd")

    p_r = sub.add_parser("render")
    p_r.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p_r.add_argument("--data", default=DEFAULT_DATA_DIR)
    p_r.add_argument("--out", default=MORNING_FILE)
    p_r.add_argument("--archive", action="store_true",
                     help="渲染前先把 >N 天的 done 项归档（晨跑用）")

    p_a = sub.add_parser("archive")
    p_a.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p_a.add_argument("--data", default=DEFAULT_DATA_DIR)

    p_re = sub.add_parser("report")
    p_re.add_argument("--from", required=True, dest="from_date")
    p_re.add_argument("--to", required=True, dest="to_date")
    p_re.add_argument("--group-by", default="parent",
                      choices=["parent", "type", "source", "assignee"])
    p_re.add_argument("--metric", default="completed",
                      choices=["completed", "created", "all"])
    p_re.add_argument("--format", default="md", choices=["md", "csv"])
    p_re.add_argument("--data", default=DEFAULT_DATA_DIR)
    p_re.add_argument("--out")

    p_e = sub.add_parser("export-csv")
    p_e.add_argument("--data", default=DEFAULT_DATA_DIR)
    p_e.add_argument("--out", default="todos.csv")

    args = parser.parse_args()
    if args.cmd == "render":
        if getattr(args, "archive", False):
            n = archive(args.data, args.days)
            print(f"[archive] 已归档 {n} 项（> {args.days} 天）")
        print(render(args.data, args.days, args.out))
    elif args.cmd == "archive":
        n = archive(args.data, args.days)
        print(f"已归档 {n} 项（> {args.days} 天）")
    elif args.cmd == "report":
        content = report(args.data, args.from_date, args.to_date,
                         args.group_by, args.metric, args.format)
        if args.out:
            with open(os.path.join(args.data, args.out), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"报表已写入 {args.out}")
        else:
            print(content)
    elif args.cmd == "export-csv":
        out = export_csv(args.data, args.out)
        print(f"已导出 {out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
