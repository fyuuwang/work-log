#!/usr/bin/env python3
"""
read_trace.py — 从 WorkBuddy traces 中提取会话上下文摘要

用法:
  python read_trace.py --session <session-uuid>
  python read_trace.py --date   <YYYY-MM-DD>

输出: 每个会话的结构化摘要（user_query + AI 关键产出），用于写工作日志时补充上下文。
仅提取关键信息（约 1-2KB/会话），不输出完整 trace 内容。
"""

import json, os, re, sys, argparse
from datetime import datetime, timezone
from collections import defaultdict

TRACES_ROOT = os.path.expanduser("~/.workbuddy/traces")


def find_trace_files(session_id=None, target_date=None):
    """遍历 traces/ 目录, 找到匹配的 trace 文件。"""
    matches = []
    target_date_obj = None
    if target_date:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

    if not os.path.isdir(TRACES_ROOT):
        return matches

    for dname in os.listdir(TRACES_ROOT):
        dpath = os.path.join(TRACES_ROOT, dname)
        if not os.path.isdir(dpath):
            continue
        for fname in os.listdir(dpath):
            if not fname.endswith(".json"):
                continue
            fp = os.path.join(dpath, fname)
            try:
                data = json.load(open(fp, "r", encoding="utf-8"))
            except Exception:
                continue

            trace = data.get("trace", {})
            sid = trace.get("sessionId", "")

            # --session mode
            if session_id and sid == session_id:
                matches.append((fp, data, sid))
                continue

            # --date mode: check startedAt
            if target_date_obj:
                started = trace.get("startedAt", "")
                if started:
                    try:
                        d = datetime.fromisoformat(started.replace("Z", "+00:00")).date()
                        if d == target_date_obj:
                            matches.append((fp, data, sid))
                    except (ValueError, AttributeError):
                        pass

    return matches


def extract_user_queries(tool_input_str):
    """从 toolInput 字符串中提取所有 <user_query> 内容。
    跳过系统提示词中的格式描述（<user_query> 第一次出现在靠近开头时）。
    返回列表（按出现顺序），只保留实际用户提问。"""
    # 找到所有 <user_query> 标签及其在字符串中的位置
    matches = list(re.finditer(r"<user_query>(.*?)</user_query>", tool_input_str, re.DOTALL))
    results = []
    for m in matches:
        content = m.group(1).strip()
        if not content:
            continue
        # 跳过系统提示词中的格式示例（出现在字符串靠前位置且内容极长）
        # 系统提示词通常在 toolInput 的前半部分，内容是 AI system prompt
        if m.start() < len(tool_input_str) * 0.6 and len(content) > 500:
            continue
        results.append(content)
    return results


def extract_ai_response(tool_output_str):
    """从 toolOutput 字符串中提取 AI 回答内容。"""
    if not tool_output_str:
        return ""
    # 查找 choices[0].message.content
    m = re.search(
        r'"role"\s*:\s*"assistant"\s*,\s*"content"\s*:\s*"((?:[^"\\]|\\.)*)"',
        tool_output_str, re.DOTALL
    )
    if m:
        content = m.group(1)
        # 转义还原
        content = content.replace("\\n", "\n").replace("\\r", "").replace('\\"', '"').replace("\\\\", "\\")
        return content.strip()
    return ""


def summarize_session(traces_data):
    """对一个会话的所有 trace 数据生成结构化摘要。"""
    # traces_data: list of (filepath, data_dict, session_id)
    if not traces_data:
        return None

    sid = traces_data[0][2]
    
    # 收集所有 generation 跨度，按时间排序
    generations = []
    for fp, data, _ in traces_data:
        for span in data.get("spans", []):
            if span.get("name") != "generation" or span.get("type") != "generation":
                continue
            if span.get("status") != "ok":
                continue
            started = span.get("startedAt", "")
            ti_str = span.get("toolInput", "")
            to_str = span.get("toolOutput", "")
            if not ti_str and not to_str:
                continue
            generations.append((started, ti_str, to_str, fp))

    if not generations:
        return None

    generations.sort(key=lambda x: x[0])  # 按时间升序

    # 提取 turn 级交互
    seen_queries = set()
    turns = []
    for started, ti_str, to_str, fp in generations:
        queries = extract_user_queries(ti_str)
        if not queries:
            continue
        # 取该 generation 的最新 user_query
        latest_query = queries[-1]
        # 去重
        q_key = latest_query[:80]  # 用前 80 字判重
        if q_key in seen_queries:
            continue
        seen_queries.add(q_key)
        
        ai_resp = extract_ai_response(to_str)
        # 截取 AI 回答关键部分（前 500 字以内）
        ai_summary = ai_resp[:500] if ai_resp else ""
        
        turns.append({
            "turn": len(turns) + 1,
            "user_asked": latest_query,
            "ai_key_output": ai_summary
        })

    return {"session_id": sid, "turns": turns}


def main():
    parser = argparse.ArgumentParser(description="从 traces 提取会话上下文摘要")
    parser.add_argument("--session", help="会话 UUID")
    parser.add_argument("--date", help="日期 YYYY-MM-DD")

    args = parser.parse_args()
    if not args.session and not args.date:
        print("请提供 --session 或 --date")
        sys.exit(1)

    trace_files = find_trace_files(session_id=args.session, target_date=args.date)
    if not trace_files:
        print("[]  # 未找到匹配的 trace 文件")
        return

    # 按 session_id 分组
    sessions = defaultdict(list)
    for fp, data, sid in trace_files:
        sessions[sid].append((fp, data, sid))

    results = []
    for sid, traces_list in sorted(sessions.items()):
        summary = summarize_session(traces_list)
        if summary and summary["turns"]:
            results.append(summary)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
