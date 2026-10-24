# -*- coding: utf-8 -*-
"""把 .github/workflows/daily.yml 里的 cron 解析成「北京时间时刻表」，供页面显示。

为什么不在前端写死时刻表：写死就一定会和 yml 脱节 —— 改了 cron 忘了改 JS，
页面上就会一本正经地显示错误的下次更新时间。这里以 yml 为唯一真相源。

只解析本工作流实际用到的写法（标准 5 段 cron，支持 * / a-b / 逗号列表），
遇到看不懂的表达式直接跳过，不猜。
"""
import os
import re

CRON_RE = re.compile(r'^\s*-\s*cron:\s*["\']([^"\']+)["\']', re.M)
WORKFLOW = os.path.join(".github", "workflows", "daily.yml")


def _expand(field, lo, hi):
    """展开一个 cron 字段：'*' / '1-5' / '1,3,5' / '7'。"""
    field = field.strip()
    if field == "*":
        return list(range(lo, hi + 1))
    out = set()
    for part in field.split(","):
        part = part.strip()
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                out.update(range(int(a), int(b) + 1))
            else:
                out.add(int(part))
        except ValueError:
            continue
    return sorted(out)


def parse_cron(expr):
    """标准 5 段 cron → [(分钟数, 星期)]，星期用 1=周一 … 7=周日。"""
    parts = expr.split()
    if len(parts) != 5:
        return None
    mi, hr, _dom, _mon, dow = parts
    mins, hrs = _expand(mi, 0, 59), _expand(hr, 0, 23)
    # cron 里 0 和 7 都是周日
    dows = sorted({7 if d in (0, 7) else d for d in _expand(dow, 0, 7)})
    if not (mins and hrs and dows):
        return None
    return [(h * 60 + m, d) for h in hrs for m in mins for d in dows]


def _to_beijing(utc_min, dow):
    """UTC 时刻 → 北京时间。跨零点时星期要往后挪一天（工作日里最典型的是 15:17 那次）。"""
    total = utc_min + 8 * 60
    extra, total = divmod(total, 1440)
    d = dow + extra
    while d > 7:
        d -= 7
    return total, d


def from_workflow(root="."):
    """返回 {"runs": [[dow, "HH:MM"], ...], "tods": [...], "weekdays": [...]}。

    读不到文件时返回 None —— 页面会自动降级成不显示「下次更新」，不影响其它内容。
    """
    path = os.path.join(root, WORKFLOW)
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return None

    runs = set()
    for m in CRON_RE.finditer(txt):
        parsed = parse_cron(m.group(1))
        if not parsed:
            continue
        for utc_min, dow in parsed:
            runs.add(_to_beijing(utc_min, dow))
    if not runs:
        return None

    out = [[dow, "%02d:%02d" % divmod(mo, 60)] for mo, dow in sorted(runs)]
    tods = sorted({t for _d, t in out})
    weekdays = sorted({d for d, _t in out})
    return {"runs": out, "tods": tods, "weekdays": weekdays,
            "tz": "Asia/Shanghai", "source": WORKFLOW}
