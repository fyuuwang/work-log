#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_todo.py —— work-log 待办机械层（纯标准库，零依赖）

子命令：
  render      生成晨报 morning.md（--no-done 跳过已完成节；--archive 先归档）
  archive     把 >N 天的 done 项移入 archive.json（只动 done，安全）
  validate    校验 todos.json / archive.json 数据完整性（摄取后跑，防 JSON 损坏）
  report      按日期范围 + 维度统计（parent/type/source/assignee）
  export-csv  导出全部待办为 CSV（供 Excel 透视）

设计原则：机械、确定性、零语义判断。展示层格式由本脚本统一产出，AI 不二次加工。
"""
import argparse
import csv
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta

# ---- 默认路径（数据根：优先读同目录 config.json 的 data_root，可用 --data 覆盖）----
def _load_config_data_root():
    """读 config.json 的 data_root；缺失返回 None。兼容两种布局：
    - config 与脚本同目录；
    - skill 标准结构：脚本在 scripts/ 下，config.json 在 skill 根（上一级）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "config.json"),
        os.path.join(here, "..", "config.json"),
    ]
    for cfg_path in candidates:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("data_root")
            except Exception:
                return None
    return None


DEFAULT_DATA_DIR = _load_config_data_root()  # None 表示未配置，运行时需 --data 或先 setup


def _resolve_data_dir(data_arg):
    """解析数据根：--data 优先；否则用 config.json；都没有则明确报错。"""
    d = data_arg or DEFAULT_DATA_DIR
    if not d:
        print("ERROR: 未解析到数据根。请传 --data <路径>，或先运行【MODE=setup】生成 config.json。",
              file=sys.stderr)
        sys.exit(2)
    return d
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
    # 统一标记约定：所有与条目关联的关键人（负责人、对接人、阻塞方/第二第三方）一律用 @X 表示，
    # 不再使用「等X」。@X 按出现顺序去重并以"；"连接；等待状态由所在分组（⏳ 等待中）体现。
    persons = []
    if it.get("assignee"):
        persons.append(it["assignee"])
    is_waiting = it.get("status") == "waiting" and it.get("waiting_for")
    if is_waiting and it["waiting_for"] not in persons:
        persons.append(it["waiting_for"])
    if persons:
        extra.append("；".join("@" + p for p in persons))
    if it.get("due_date"):
        extra.append(f"截止{it['due_date']}")
    if extra:
        s += " （" + "；".join(extra) + "）"
    return s


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
PRIORITY_RANK = {"P1": 0, "P2": 1, "P3": 2, None: 3}


def _sort_key(it):
    """组内排序：priority（P1→P3）→ due 升序 → created 升序。None 排最后。"""
    return (
        PRIORITY_RANK.get(it.get("priority"), 3),
        d(it.get("due_date")) is None,   # 有 due 的优先
        d(it.get("due_date")) or date.max,
        it.get("created_date") or "",
    )


def _group_items(items, move_other_last=True):
    """按 parent 分组（保持首次出现顺序）；'其他'除非有 P1 项，否则排到最后。"""
    groups, gmap = [], {}
    for it in items:
        p = it.get("parent") or "其他"
        if p not in gmap:
            gmap[p] = []
            groups.append(p)
        gmap[p].append(it)
    if move_other_last and "其他" in gmap:
        has_p1 = any(
            it.get("priority") and "P1" in str(it.get("priority"))
            for it in gmap["其他"]
        )
        if not has_p1:
            groups.remove("其他")
            groups.append("其他")
    return groups, gmap


def _render_group(lines, groups, gmap, prefix="  - [ ] "):
    """渲染一组 parent 分组条目（含 subgroup 二级分组标题）。"""
    for idx, p in enumerate(groups, 1):
        items_in_p = sorted(gmap[p], key=_sort_key)
        lines.append(f"### {cn_num(idx)}、{p}")
        last_sg = None
        for it in items_in_p:
            sg = it.get("subgroup") or ""
            if sg and sg != last_sg:
                if last_sg is not None:
                    lines.append("")
                lines.append(f"**{sg}**")
                lines.append("")
                last_sg = sg
            elif not sg and last_sg != "":
                if last_sg is not None:
                    lines.append("")
                last_sg = ""
            lines.append(prefix + fmt_item(it))


def render(data_dir, days, out_name=MORNING_FILE, no_done=False, done_full=False):
    todo_path = os.path.join(data_dir, TODO_FILE)
    data = load(todo_path)
    items = data.get("items", [])
    t = today()
    cutoff = t - timedelta(days=days)

    open_items = [i for i in items if i.get("status") == "open"]
    waiting_items = [i for i in items if i.get("status") == "waiting"]
    recent_done = [
        i for i in items
        if i.get("status") == "done" and (d(i.get("completed_date")) or t) >= cutoff
    ]

    lines = []
    lines.append(f"# 晨间待办 · {t.isoformat()}")
    lines.append("")
    stats = f"🔴 进行中 {len(open_items)} 项"
    if waiting_items:
        stats += f" ｜ ⏳ 等待中 {len(waiting_items)} 项"
    stats += f" ｜ ✅ 已完成 {len(recent_done)} 项"
    lines.append(f"**进度概览**：{stats}")
    lines.append("")

    # ---- 进行中（我要做，open）----
    lines.append("## 进行中（我要做）")
    if not open_items:
        lines.append("_无_")
    else:
        groups, gmap = _group_items(open_items)
        _render_group(lines, groups, gmap)
    lines.append("")

    # ---- 等待中（等别人，waiting）----
    if waiting_items:
        lines.append(f"## ⏳ 等待中（等别人，{len(waiting_items)} 项）")
        groups, gmap = _group_items(waiting_items)
        _render_group(lines, groups, gmap)
        lines.append("")

    # ---- 已完成（近 N 天）：--no-done 跳过 / --done-full 全量 / 默认摘要 ----
    if not no_done:
        lines.append(f"## 已完成（近 {days} 天，{len(recent_done)} 项）")
        if not recent_done:
            lines.append("_无_")
        elif done_full:
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
        else:
            # 摘要模式（默认）：按板块计数 + 最近 5 条明细
            cnt = {}
            for it in recent_done:
                p = it.get("parent") or "其他"
                cnt[p] = cnt.get(p, 0) + 1
            by_count = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))
            lines.append("**按板块**：" + " ｜ ".join(f"{p} {n}" for p, n in by_count))
            recent5 = sorted(recent_done, key=lambda x: d(x.get("completed_date")) or t, reverse=True)[:5]
            lines.append("**最近完成**：")
            for it in recent5:
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
            lines.append(f"> 完整列表：`python render_todo.py render --done-full`")
        lines.append("")

    # ---- 待提醒：进行中设了 due_date 的项，区分已逾期 / 未到期 ----
    remind = [i for i in open_items + waiting_items if i.get("due_date")]
    if remind:
        overdue = [i for i in remind if d(i.get("due_date")) and d(i.get("due_date")) < t]
        upcoming = [i for i in remind if not (d(i.get("due_date")) and d(i.get("due_date")) < t)]
        overdue.sort(key=lambda x: d(x.get("due_date")) or t)
        upcoming.sort(key=lambda x: d(x.get("due_date")) or t)
        lines.append("## ⏰ 待提醒（设了截止日）")
        if overdue:
            lines.append(f"### ⚠️ 已逾期（{len(overdue)} 项）")
            for it in overdue:
                due = it.get("due_date") or ""
                days_late = (t - d(due)).days if d(due) else 0
                parent = it.get("parent") or "其他"
                line = f"  ⚠️ {due} ｜ 超 {days_late} 天 ｜ - [ ] {it.get('title', '')} - {parent}"
                extra = []
                if it.get("assignee"):
                    extra.append("@" + it["assignee"])
                if it.get("supplier"):
                    extra.append("供应商:" + it["supplier"])
                if extra:
                    line += " （" + "；".join(extra) + "）"
                lines.append(line)
            lines.append("")
        if upcoming:
            lines.append("### ⏳ 未到期")
            for it in upcoming:
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
# validate
# ---------------------------------------------------------------------------
VALID_TYPES = {"需求", "开发", "采购", "审批", "会议", "文档", "沟通", "运维", "其他"}
VALID_SOURCES = {"领导交办", "会议", "自查", "供应商", "其他"}
VALID_STATUS = {"open", "waiting", "done"}
VALID_PRIORITY = {"P1", "P2", "P3"}
REQUIRED_FIELDS = ["id", "title", "parent", "type", "source", "status",
                   "created_date", "updated_date"]
DATE_FIELDS = ["created_date", "updated_date", "started_date",
               "completed_date", "due_date"]


def validate(data_dir):
    """校验 todos.json / archive.json 数据完整性。errors>0 退出码 1。"""
    todo_path = os.path.join(data_dir, TODO_FILE)
    arch_path = os.path.join(data_dir, ARCHIVE_FILE)
    problems, errors, warns = [], 0, 0

    for path, label in [(todo_path, "todos.json"), (arch_path, "archive.json")]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors += 1
            problems.append(f"[ERROR] {label} JSON 解析失败: {e}")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            errors += 1
            problems.append(f"[ERROR] {label} 结构非法（应为 {{\"items\": [...]}}）")
            continue
        if label == "todos.json":
            problems.extend(_validate_items(data.get("items", []), label))
    for p in problems:
        if p.startswith("[ERROR]"):
            errors += 1
        elif p.startswith("[WARN]"):
            warns += 1

    if not problems:
        print(f"✓ todos.json / archive.json 校验通过（{errors} 错误 / {warns} 警告）")
        return 0
    print(f"校验发现 {errors} 个错误 / {warns} 个警告：")
    for p in problems:
        print("  " + p)
    return 1 if errors else 0


def _validate_items(items, label):
    """逐条校验（返回问题列表）。"""
    problems, seen_ids = [], {}
    for it in items:
        itid = it.get("id") or "?"
        for f in REQUIRED_FIELDS:
            if not it.get(f):
                problems.append(f"[ERROR] {label} {itid}: 缺少必填字段 {f}")
        if itid in seen_ids:
            problems.append(f"[ERROR] {label} 重复 id {itid}（{seen_ids[itid]} / {it.get('title', '')}）")
        seen_ids[itid] = it.get("title", "")

        if it.get("type") and it["type"] not in VALID_TYPES:
            problems.append(f"[WARN] {itid}: type '{it['type']}' 不在默认词表（若是新增词，请补入 categories.md）")
        if it.get("source") and it["source"] not in VALID_SOURCES:
            problems.append(f"[WARN] {itid}: source '{it['source']}' 不在默认词表（若是新增词，请补入 categories.md）")
        if it.get("status") and it["status"] not in VALID_STATUS:
            problems.append(f"[ERROR] {itid}: status '{it['status']}' 非法（应为 open/waiting/done）")
        if it.get("priority") and it["priority"] not in VALID_PRIORITY:
            problems.append(f"[WARN] {itid}: priority '{it['priority']}' 非法（应为 P1/P2/P3）")
        if "reviewed" in it and not isinstance(it.get("reviewed"), bool):
            problems.append(f"[WARN] {itid}: reviewed 应为布尔值")

        for df in DATE_FIELDS:
            v = it.get(df)
            if v and not d(v):
                problems.append(f"[ERROR] {itid}: {df} 格式非法 '{v}'（应为 YYYY-MM-DD）")

        status = it.get("status")
        if status == "done" and not it.get("completed_date"):
            problems.append(f"[WARN] {itid}: status=done 但无 completed_date")
        if it.get("completed_date") and status != "done":
            problems.append(f"[WARN] {itid}: 有 completed_date 但 status={status}（应为 done）")
        if it.get("waiting_for") and status == "open":
            problems.append(f"[WARN] {itid}: waiting_for 非空但 status=open（建议改 waiting）")
        if status == "waiting" and not it.get("waiting_for"):
            problems.append(f"[WARN] {itid}: status=waiting 但 waiting_for 为空")
        if "tags" in it and not isinstance(it.get("tags"), list):
            problems.append(f"[WARN] {itid}: tags 应为数组")
    return problems


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
FIELDS = ["id", "title", "parent", "subgroup", "type", "source", "status", "priority",
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
    p_r.add_argument("--no-done", action="store_true",
                     help="跳过'已完成'节（摄取反馈精简用）")
    p_r.add_argument("--done-full", action="store_true",
                     help="'已完成'节输出全量列表（默认只出摘要：板块计数+最近5条）")

    p_a = sub.add_parser("archive")
    p_a.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p_a.add_argument("--data", default=DEFAULT_DATA_DIR)

    p_v = sub.add_parser("validate",
                         help="校验 todos.json / archive.json 数据完整性（摄取后跑）")
    p_v.add_argument("--data", default=DEFAULT_DATA_DIR)

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
    data_dir = _resolve_data_dir(args.data)
    if args.cmd == "render":
        if getattr(args, "archive", False):
            n = archive(data_dir, args.days)
            print(f"[archive] 已归档 {n} 项（> {args.days} 天）")
        print(render(data_dir, args.days, args.out,
                     no_done=getattr(args, "no_done", False),
                     done_full=getattr(args, "done_full", False)))
    elif args.cmd == "archive":
        n = archive(data_dir, args.days)
        print(f"已归档 {n} 项（> {args.days} 天）")
    elif args.cmd == "validate":
        sys.exit(validate(data_dir))
    elif args.cmd == "report":
        content = report(data_dir, args.from_date, args.to_date,
                         args.group_by, args.metric, args.format)
        if args.out:
            with open(os.path.join(data_dir, args.out), "w", encoding="utf-8") as f:
                f.write(content)
            print(f"报表已写入 {args.out}")
        else:
            print(content)
    elif args.cmd == "export-csv":
        out = export_csv(data_dir, args.out)
        print(f"已导出 {out}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
