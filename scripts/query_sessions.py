import sqlite3, json, datetime

db = r'C:\Users\DESKTOP-4\.workbuddy\workbuddy.db'
conn = sqlite3.connect(db)

# 查表
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [r[0] for r in cur.fetchall()])

# sessions 表结构
cur = conn.execute('PRAGMA table_info(sessions)')
cols = cur.fetchall()
print('sessions cols:', [(c[1],c[2]) for c in cols])

# created_at/updated_at 是 Unix 毫秒时间戳
def ts_to_date(ts):
    if ts is None:
        return 'NULL'
    return datetime.datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')

# 查今天的所有会话 (2026-07-20)
today_ms_start = 2026072000000  # placeholder
import datetime as dt
today = dt.date(2026, 7, 20)
today_start = int(dt.datetime(today.year, today.month, today.day, tzinfo=dt.timezone.utc).timestamp() * 1000)
today_end = today_start + 86400000 - 1

cur = conn.execute(
    "SELECT id, created_at, updated_at, title, cwd, status FROM sessions WHERE (created_at >= ? AND created_at <= ?) OR (updated_at >= ? AND updated_at <= ?) ORDER BY created_at",
    (today_start, today_end, today_start, today_end)
)
rows = cur.fetchall()
print(f'\nToday (2026-07-20) sessions ({len(rows)}):')
for r in rows:
    print(f'  {r[0][:12]}... | created={ts_to_date(r[1])} | updated={ts_to_date(r[2])} | title={str(r[3])[:80]} | cwd={str(r[4])[:50]} | status={r[5]}')

# LOOKBACK: 2026-07-17 to 2026-07-20
lookback_start = int(dt.datetime(2026, 7, 17, tzinfo=dt.timezone.utc).timestamp() * 1000)
lookback_end = today_end

print(f'\n\nLOOKBACK window (2026-07-17 to 2026-07-20):')
cur = conn.execute(
    "SELECT id, created_at, updated_at, title, cwd, status FROM sessions WHERE created_at >= ? AND created_at <= ? ORDER BY created_at",
    (lookback_start, lookback_end)
)
rows = cur.fetchall()
print(f'Total: {len(rows)}')
for r in rows:
    print(f'  {r[0]} | created={ts_to_date(r[1])} | updated={ts_to_date(r[2])} | title={str(r[3])[:80]} | cwd={str(r[4])[:50]} | status={r[5]}')

conn.close()
