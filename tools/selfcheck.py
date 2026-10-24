# -*- coding: utf-8 -*-
"""交付前自检：数据、结构与渲染一致性。全部通过才算过。"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..", "docs", "index.html")
fails, warns = [], []


def bad(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


h = io.open(SITE, encoding="utf-8").read()

# ---------- 1. 结构 ----------
for tag in ("<!DOCTYPE html>", 'charset="utf-8"', 'name="color-scheme"', 'id="grid"',
            'id="chart"', 'id="hero"', 'id="macro"', 'id="meta"'):
    if tag not in h:
        bad(f"缺少结构标记 {tag}")

# ---------- 2. CSS 花括号平衡 ----------
css = re.search(r"<style>(.*?)</style>", h, re.S)
if not css:
    bad("找不到 <style> 块")
else:
    c = css.group(1)
    if c.count("{") != c.count("}"):
        bad(f"CSS 花括号不平衡 {c.count('{')} vs {c.count('}')}")
    # 亮色残留检查（高级黑主题不该出现大块浅色底）
    for bad_c in ("#fff;", "background:#f", "background: #f", "#ffffff;"):
        if bad_c in c:
            warn(f"CSS 中出现可能的浅色底 {bad_c}")

# ---------- 3. 内联数据可解析 ----------
key = "window.__DATA__ = "
i = h.index(key) + len(key)
j = h.index(";</script>", i)
try:
    data = json.loads(h[i:j])
except Exception as e:  # noqa: BLE001
    bad(f"内联 JSON 解析失败 {e}")
    data = {}

if "</script>" in h[i:j]:
    bad("内联 JSON 里出现未转义的 </script>")

latest = data.get("latest") or {}
hist = data.get("history") or []
series = data.get("series") or {}
assets = latest.get("assets") or []

if len(assets) != 5:
    bad(f"标的数量应为 5，实际 {len(assets)}")
if len(hist) < 60:
    bad(f"历史期数过少 {len(hist)}")

# ---------- 4. 单标的数据完整性 ----------
need = ("id", "name", "score", "multiplier", "label", "band_pos", "dimensions",
        "price", "price_date", "advisory_only", "gates")
for a in assets:
    for k in need:
        if k not in a:
            bad(f"{a.get('name','?')} 缺字段 {k}")
    s = a.get("score")
    if not isinstance(s, (int, float)) or not (0 <= s <= 100):
        bad(f"{a.get('name')} 分数异常 {s}")
    if a.get("multiplier") is None:
        bad(f"{a.get('name')} 倍数为空")
    dims = a.get("dimensions") or []
    if len(dims) != 4:
        bad(f"{a.get('name')} 维度数 {len(dims)} != 4")
    wsum = sum(d.get("weight", 0) for d in dims)
    if abs(wsum - 100) > 1.5:
        bad(f"{a.get('name')} 维度权重和 {wsum} != 100")
    for d in dims:
        if not d.get("metrics"):
            bad(f"{a.get('name')}/{d.get('key')} 无指标")
        if not (0 <= d.get("score", -1) <= 100):
            bad(f"{a.get('name')}/{d.get('key')} 维度分异常 {d.get('score')}")
        for m in d.get("metrics") or []:
            if m.get("raw") is None and m.get("pct") is None:
                warn(f"{a.get('name')}/{m.get('name')} 原始值与分位皆空")
            if m.get("pct") is not None and not (0 <= m["pct"] <= 100):
                bad(f"{a.get('name')}/{m.get('name')} 分位越界 {m['pct']}")

# ---------- 4b. 近一月涨跌轨迹（纯展示，但错了会直接画歪） ----------
for a in assets:
    m = a.get("month")
    if not m:
        warn(f"{a.get('name')} 没有近一月轨迹，该卡片会少一条走势")
        continue
    pts = m.get("pts") or []
    if len(pts) < 8:
        bad(f"{a.get('name')} 轨迹点数过少 {len(pts)}")
    # 首点必须是 0%（基准 = 窗口前一日收盘），否则「近一月涨跌」和图对不上
    if pts and abs(pts[0][1]) > 0.011:
        bad(f"{a.get('name')} 轨迹首点应为 0%，实际 {pts[0][1]}")
    ds = [p[0] for p in pts]
    if ds != sorted(ds):
        bad(f"{a.get('name')} 轨迹日期非升序")
    if m.get("chg_week") is None:
        bad(f"{a.get('name')} 缺近 7 天涨跌")
    if m.get("week_from") not in ds:
        bad(f"{a.get('name')} week_from={m.get('week_from')} 不在轨迹里，前端高亮段会从 0 画起")
    if abs((pts[-1][1] if pts else 0) - (m.get("chg_month") or 0)) > 0.011:
        bad(f"{a.get('name')} 轨迹末点与 chg_month 不一致")

if 'class="chart mchart"' not in h:
    warn("页面上没有近一月对比图（标的轨迹不足两条时会自动隐藏）")

# ---------- 4c. 跑批时刻表（决定页头显示「下次自动更新」） ----------
sch = data.get("schedule")
if not sch or not sch.get("runs"):
    warn("payload 缺 schedule，页头不会显示「下次自动更新」（检查 workflow 的 cron 能否解析）")
else:
    tods = sch.get("tods") or []
    if len(tods) < 2:
        warn(f"从 cron 只解析出 {tods} 个时刻，工作流可能写错了")
    # 整点/半点是最容易被 GitHub 丢弃的时段，出现就提醒（不阻断，理论上有意为之另说）
    for t in tods:
        if t.endswith(":00") or t.endswith(":30"):
            warn(f"cron 时刻 {t} 踩在整点/半点上，GitHub 高峰期容易丢触发")

# ---------- 4d. 美股市场情绪（纯展示，缺了不影响分数） ----------
mood = latest.get("mood")
if not mood:
    warn("没有 CNN 恐惧与贪婪数据（仅展示项；该区块会自动隐藏，其它内容不受影响）")
else:
    s = mood.get("score")
    if not isinstance(s, (int, float)) or not (0 <= s <= 100):
        bad(f"情绪指数分数异常 {s}")
    if not mood.get("label") or not mood.get("zones"):
        bad("情绪指数缺 label / zones，页面上的区间条画不出来")
    else:
        lo, hi = mood.get("zone") or [-1, -1]
        # 分数必须落在它自己声明的区间里：否则指针停在"恐惧"、文字却写"极度恐惧"，自相矛盾
        if not (lo <= (s or -1) <= hi):
            bad(f"情绪指数 {s} 不在声明的区间 {lo}-{hi} 内")
        if len(mood.get("zones") or []) != 5:
            bad(f"情绪指数区间应为 5 档，实际 {len(mood.get('zones') or [])}")

# ---------- 5. 曲线与当天一致性 ----------
# payload.history 每项只有 trade_date（画 x 轴用），分数末点在 series 里
if hist and hist[-1].get("trade_date") != latest.get("trade_date"):
    warn(f"历史末点 {hist[-1].get('trade_date')} 与数据日 {latest.get('trade_date')} 不一致")
la = {a["id"]: a["score"] for a in assets}
diff = []
for aid, pts in (series.get("data") or {}).items():
    if not pts or aid not in la:
        continue
    if pts[-1]["d"] != latest.get("trade_date"):
        warn(f"{aid} 序列末点 {pts[-1]['d']} 落后于数据日 {latest.get('trade_date')}")
    if abs(pts[-1]["s"] - la[aid]) > 2:
        diff.append(f"{aid} 序列{pts[-1]['s']:.1f} vs 实时{la[aid]:.1f}")
if diff:
    bad("曲线末点与实时分数偏差过大：" + "；".join(diff))

# ---------- 6. 序列点数和日期顺序 ----------
for aid, pts in (series.get("data") or {}).items():
    if len(pts) != len(hist):
        warn(f"{aid} 序列 {len(pts)} 点，历史 {len(hist)} 期，前端按索引绘图会错位")
    ds = [p["d"] for p in pts]
    if ds != sorted(ds):
        bad(f"{aid} 序列日期非升序")
    if any(p["s"] is None for p in pts):
        bad(f"{aid} 序列存在空分数")

# ---------- 7. JS 语法（抽出最后一个 script 供 node --check） ----------
blocks = re.findall(r"<script>(.*?)</script>", h, re.S)
if len(blocks) < 2:
    bad(f"script 块数异常 {len(blocks)}")
else:
    io.open(os.path.join(HERE, "_selfcheck.js"), "w", encoding="utf-8").write(blocks[-1])

# ---------- 8. 体积 ----------
size_kb = len(h.encode("utf-8")) / 1024
if size_kb > 400:
    warn(f"页面 {size_kb:.0f} KB 偏大，移动端首屏可能慢")

print(f"页面 {size_kb:.1f} KB · 标的 {len(assets)} · 历史 {len(hist)} 期 · 序列 "
      f"{len(series.get('data') or {})} 条")
for a in assets:
    print(f"  {a['name'][:26]:28s} {a['score']:5.1f} 分  {a['multiplier']:.1f}×  "
          f"档内 {(a.get('band_pos') or 0):3.0f}%  维度 "
          + "/".join(f"{d['score']:.0f}" for d in a['dimensions']))

if warns:
    print("\n[警告]")
    for w in warns:
        print("  ·", w)
if fails:
    print("\n[失败]")
    for f in fails:
        print("  ✗", f)
    sys.exit(1)
print("\n自检通过")
