# -*- coding: utf-8 -*-
"""超短线擒龙：热点题材 → 龙头梯队 → 异动监控 → 补涨候选。

纯展示模块，不参与打分、不影响倍率。任何一块失败都吞掉并记 note，绝不拖累主跑批。

数据源（全部东方财富公开接口，GitHub Runner 与本地均可访问）：
  · 涨停板池 push2ex.eastmoney.com/getTopicZTPool —— 当日涨停股：
      连板数(lbc) / 封板时间(fbt) / 封单资金(fund) / 炸板次数(zbc) / 换手率(hs) / 行业(hybk)
  · 炸板池   getTopicZBPool —— 涨停后打开 = 龙头「异动」信号
  · 跌停池   getTopicDTPool —— 情绪温度（冰点/退潮）
  · 概念板块涨幅榜 push2.eastmoney.com/api/qt/clist/get fs=m:90+t:3 —— 题材温度
  · 行业成分股   push2.eastmoney.com/api/qt/clist/get fs=b:BKxxxx —— 补涨候选

方法论（从两个真实题材案例提炼，非拍脑袋）：
  AI短剧/漫剧（2026-10~11）：10-14 传媒/游戏批量涨停→题材爆发；新经典/慈文传媒 4 连板、
    浙文影业（11-05 一字 4 连板、78 万手封单）+引力传媒 4天3板 为龙头；中文在线、捷成股份
    （20CM）、龙版传媒、上海电影、奥飞娱乐等为跟风/补涨。
  创新药（2025-05~07）：三生国健（5-19 启动、4 连板 20CM）→ 舒泰神（5-21 启动、主升 4 倍）为
    首发龙头；随后昂利康（6 月 3 连板）、常山药业（累计 +147.69%）、广生堂（7 月 4 连板 20CM）、
    塞力医疗（4 连板、周 +51.55%）、联环药业为「接力龙头」。永安药业/交大昂立是「先于龙」
    （其他逻辑先涨、身位优势）。
  规律：题材按「涨停家数」计（涨停潮）；龙头 = 最高连板 + 最强封板；异动 = 炸板/断板/高换手；
        补涨 = 龙头高位后资金找同题材低位股（首板跟风 / 接力龙头 / 未板补涨）。

字段口径：
  · 价格 p 接口单位为厘（7020 = 7.02 元），一律 /1000
  · 封板时间 fbt 为 HHMMSS（92500 = 09:25:00）
  · 封单资金 fund / 成交额 amount 单位为元，展示时换算成「亿元」
  · 涨停统计 zttj = {days, ct} → 「N 天 M 板」；连板数 lbc 是「当前连续涨停天数」
"""
import datetime as dt
import time

from .net import fetch_json

UT = "7eea3edcaed734bea9cbfc24409ed989"
DOT = "wz.ztzt"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

_ZT_FIELDS = ("c", "n", "p", "zdp", "amount", "ltsz", "hs", "lbc", "fbt", "lbt",
              "fund", "zbc", "hybk", "zttj")


def _get_json(url, retries=3):
    """东财接口会间歇性断连，带退避重试。"""
    last = None
    for i in range(retries):
        try:
            return fetch_json(url, headers=UA, timeout=20, retries=2)
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(1.5 + i * 2.0)
    raise last


def _pool(kind, date, pagesize=400):
    """涨停/炸板/跌停池。kind: zt / zb / dt。"""
    # getTopicZTPool / getTopicZBPool / getTopicDTPool
    map_ = {"zt": "ZTPool", "zb": "ZBPool", "dt": "DTPool"}
    name = map_[kind]
    sort = "fbt:asc" if kind in ("zt", "zb") else "fund:asc"
    url = (f"https://push2ex.eastmoney.com/getTopic{name}?ut={UT}&dpt={DOT}"
           f"&Pageindex=0&pagesize={pagesize}&sort={sort}&date={date}")
    js = _get_json(url)
    data = js.get("data")
    if not data:
        return []
    return data.get("pool") or []


def _latest_date():
    """从今天（北京时间）往回找最近一个有涨停数据的交易日。

    盘前（如 09:15）当日涨停池尚未生成，自动回退到上一交易日 —— 这正是盘前需要看的
    「昨日复盘 / 连板梯队」。节假日/周末同样回退。
    """
    today = dt.date.today()
    # 北京时间可能比 UTC 早一天，用 UTC+8 校准
    cn = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)
    today = cn.date()
    for back in range(0, 12):
        d = today - dt.timedelta(days=back)
        dstr = d.strftime("%Y%m%d")
        try:
            pool = _pool("zt", dstr)
            if pool:
                return dstr, pool
        except Exception:  # noqa: BLE001
            continue
    return today.strftime("%Y%m%d"), []


def _fmt_time(t):
    try:
        t = int(t)
        return f"{t // 10000:02d}:{t % 10000 // 100:02d}"
    except (TypeError, ValueError):
        return ""


def _yi(v):
    """元 → 亿元字符串。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if v >= 1e8:
        return f"{v / 1e8:.2f}亿"
    if v >= 1e4:
        return f"{v / 1e4:.0f}万"
    return f"{v:.0f}"


def _zt_label(lbc):
    """连板标签：lbc=1 →「首板」，lbc>=2 →「N 连板」。"""
    return "首板" if lbc <= 1 else f"{lbc}连板"


def _zt_cycle(zttj, lbc):
    """反复活跃标记：zttj 的「N 天 M 板」，仅当 N != M（断板后再封）时返回。

    例：闽发铝业 lbc=4、zttj=9天5板 → 「9天5板」说明它 9 天里累计 5 个涨停、中途断过板，
    比「4 连板」更能体现妖股反复活跃的特征；浙文影业 4天4板 是干净连板，无需此标记。
    """
    if zttj and isinstance(zttj, dict):
        days = zttj.get("days")
        ct = zttj.get("ct")
        if days and ct and int(days) != int(ct):
            return f"{days}天{ct}板"
    return ""


def _clean_row(r, kind="zt"):
    """涨停池原始行 → 干净 dict。"""
    lbc = int(r.get("lbc") or 0)
    zttj = r.get("zttj")
    ct = int((zttj or {}).get("ct") or lbc)
    return {
        "code": str(r.get("c") or ""),
        "name": str(r.get("n") or ""),
        "price": round(float(r.get("p") or 0) / 1000, 2),
        "chg": round(float(r.get("zdp") or 0), 2),
        "hs": round(float(r.get("hs") or 0), 2),
        "hybk": str(r.get("hybk") or "—"),
        "lbc": lbc,
        "ct": ct,
        "zbc": int(r.get("zbc") or 0),
        "fund": _yi(r.get("fund")),
        "amount": _yi(r.get("amount")),
        "fbt": _fmt_time(r.get("fbt")),
        "zf": round(float(r.get("zf") or 0), 2) if r.get("zf") is not None else None,
        "label": _zt_label(lbc),
        "cycle": _zt_cycle(zttj, lbc),
    }


def _themes(pool):
    """按行业(hybk)聚合涨停家数，产出热点题材榜。

    题材按「涨停家数」计（游资口径：热点 = 涨停潮）。每个题材带最高连板与龙头。
    """
    by = {}
    for r in pool:
        k = r["hybk"]
        by.setdefault(k, {"count": 0, "max_lbc": 0, "leader": None, "rows": []})
        by[k]["count"] += 1
        if r["lbc"] > by[k]["max_lbc"]:
            by[k]["max_lbc"] = r["lbc"]
            by[k]["leader"] = r["name"]
        by[k]["rows"].append(r)
    items = []
    for name, v in by.items():
        items.append({
            "name": name,
            "count": v["count"],
            "max_lbc": v["max_lbc"],
            "leader": v["leader"],
        })
    items.sort(key=lambda x: (-x["count"], -x["max_lbc"]))
    return items


def _concept_board(top=8):
    """概念板块涨幅榜（题材温度）。"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=%d&po=1&np=1&fltt=2"
           "&invt=2&fid=f3&fs=m:90+t:3&fields=f2,f3,f12,f14" % top)
    js = _get_json(url)
    diff = ((js.get("data") or {}).get("diff")) or []
    out = []
    for it in diff:
        out.append({
            "name": it.get("f14"),
            "code": it.get("f12"),
            "chg": round(float(it.get("f3") or 0), 2),
        })
    return out


def _industry_map():
    """行业名称 → 东财行业板块代码（BKxxxx）。"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=0&np=1&fltt=2"
           "&invt=2&fid=f12&fs=m:90+t:2&fields=f12,f14")
    js = _get_json(url)
    diff = ((js.get("data") or {}).get("diff")) or []
    return {it.get("f14"): it.get("f12") for it in diff if it.get("f14")}


def _industry_members(bk, top=40):
    """行业成分股（按涨幅降序），用于找补涨候选。"""
    url = ("https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=%d&po=1&np=1&fltt=2"
           "&invt=2&fid=f3&fs=b:%s&fields=f2,f3,f8,f12,f14" % (top, bk))
    js = _get_json(url)
    diff = ((js.get("data") or {}).get("diff")) or []
    out = []
    for it in diff:
        out.append({
            "code": it.get("f12"),
            "name": it.get("f14"),
            "chg": round(float(it.get("f3") or 0), 2),
            "hs": round(float(it.get("f8") or 0), 2),
        })
    return out


def _catchup(themes, pool, ind_map, n_theme=3, n_each=4):
    """补涨候选：热点题材行业中，未涨停但涨幅居前的成分股。

    龙头连板到高位后，资金会找同题材低位股补涨；这里挑「同题材、今日上涨但没封板」的
    个股。涨停股（已在池内）与下跌股（chg<=0）排除。
    """
    zt_codes = {r["code"] for r in pool}
    out = []
    for th in themes[:n_theme]:
        bk = ind_map.get(th["name"])
        if not bk:
            continue
        try:
            members = _industry_members(bk)
        except Exception:  # noqa: BLE001
            continue
        picked = 0
        for m in members:
            if m["code"] in zt_codes:
                continue
            if m["chg"] <= 0:
                continue
            out.append({
                "theme": th["name"],
                "code": m["code"],
                "name": m["name"],
                "chg": m["chg"],
                "hs": m["hs"],
            })
            picked += 1
            if picked >= n_each:
                break
        time.sleep(0.4)
    return out


def _dragon_reason(d):
    """龙头买入理由：按「高度 + 换手 + 炸板次数」判断能否上车。"""
    lbc = d.get("lbc", 0)
    hs = d.get("hs", 0)
    zbc = d.get("zbc", 0)
    if lbc >= 4:
        return "空间龙头已高位，追高风险大，仅作风向标"
    if hs < 3:
        return f"{lbc}板一字板，封单锁死买不进"
    if zbc >= 1:
        return f"{lbc}板炸板{zbc}次后回封，弱转强可关注"
    return f"{lbc}板换手板，可等分歧转一致时介入"


def _catchup_reason(chg):
    """补涨买入理由按当日涨幅分档：真「低位」才叫补涨，已近涨停属追高。"""
    if chg < 8:
        return "同题材龙头已连板，低位补涨，可现价买入"
    if chg <= 15:
        return "同题材强势补涨，涨幅已拉开，等回踩不追高"
    return "已近涨停属追高，仅观察不追"


def _buy_top5(themes, dragon, catchup):
    """买入候选 Top5 —— 三因子打分（题材强度 30 + 可买性 40 + 资金活跃 30），取前 5。

    核心口径：这是「可以买」的榜单，不是「最热」榜单 —— 可买性权重最高，
    涨幅接近涨停（追高）的股会被大幅降权，让「低位补涨 / 换手龙头」真正排到前面。

      · 题材强度 30 分 = 所在行业涨停家数 / 当日最大涨停家数 × 30
      · 可买性 40 分：
          补涨股（未涨停）：涨幅越低越可买（<3% 满分 40，>15% 近涨停只剩 4）
          龙头：2板28 / 3板24 / 4板14 / 5板+6；一字/秒板再减 6
      · 资金活跃 30 分 = 换手 5~15% 最佳；<2% 无人气、>25% 巨量分歧，均递减
    """
    cnt = {t["name"]: t["count"] for t in themes}
    mx = max((t["count"] for t in themes), default=1)

    def _hs(hs):
        hs = max(0, hs)
        if hs <= 5:
            return hs / 5 * 30
        if hs <= 15:
            return 30
        if hs <= 25:
            return 30 - (hs - 15) * 0.8
        return max(0, 22 - (hs - 25) * 1.5)

    def _catchup_pos(chg):
        """补涨可买性：涨幅越低越可买。"""
        if chg < 3:
            return 40
        if chg <= 6:
            return 40 - (chg - 3) / 3 * 4      # 3→40，6→36
        if chg <= 9:
            return 36 - (chg - 6) / 3 * 6      # 6→36，9→30
        if chg <= 12:
            return 30 - (chg - 9) / 3 * 8      # 9→30，12→22
        if chg <= 15:
            return 22 - (chg - 12) / 3 * 10    # 12→22，15→12
        return max(0, 12 - (chg - 15) * 2.7)   # 15→12，18→4

    def _dragon_pos(d):
        lbc = d.get("lbc", 0)
        pos = {2: 28, 3: 24, 4: 14}.get(lbc, 6)
        hs = d.get("hs", 0)
        if hs < 3:
            pos -= 6  # 一字板买不进
        return pos

    def _pos_label(code):
        """北交所提示：92/83/87/43 开头门槛高、30cm 波动大。"""
        return "北交所" if code[:2] in ("92", "83", "87", "43") else ""

    cands = []
    for x in catchup:
        chg = x.get("chg", 0)
        tag = _pos_label(x["code"])
        cands.append({
            "name": x["name"], "code": x["code"], "theme": x["theme"],
            "chg": chg, "hs": x.get("hs", 0), "kind": "补涨",
            "tag": tag,
            "reason": _catchup_reason(chg) + (f"（{tag}，30cm 波动大）" if tag else ""),
            "score": round(cnt.get(x["theme"], 1) / mx * 30
                           + _catchup_pos(chg) + _hs(x.get("hs", 0)), 1),
        })
    for d in dragon:
        lbc = d.get("lbc", 0)
        tag = _pos_label(d["code"])
        cands.append({
            "name": d["name"], "code": d["code"], "theme": d.get("hybk", "—"),
            "chg": d.get("chg", 0), "hs": d.get("hs", 0),
            "kind": d.get("label", f"{lbc}连板"),
            "tag": tag,
            "reason": _dragon_reason(d),
            "score": round(cnt.get(d.get("hybk", "—"), 1) / mx * 30
                           + _dragon_pos(d) + _hs(d.get("hs", 0)), 1),
        })
    cands.sort(key=lambda x: -x["score"])
    return cands[:5]


def run():
    """拉数 + 聚合，返回可塞进 latest.json 的 zhulong 段。失败逐块吞掉。"""
    notes = []
    date, pool_raw = _latest_date()
    pool = [_clean_row(r) for r in pool_raw]

    if not pool:
        # 连往回 12 天都没有涨停数据（长假 / 接口全面失败），输出空壳 + 说明
        return {"as_of": date, "empty": True,
                "notes": ["本期未取到涨停板池数据（长假或接口不可用）"]}

    # 炸板（异动）/ 跌停（情绪）
    zb = dt_pool = []
    try:
        zb = [_clean_row(r, "zb") for r in _pool("zb", date)]
    except Exception as e:  # noqa: BLE001
        notes.append(f"炸板池取不到：{str(e)[:80]}")
    try:
        dt_pool = [_clean_row(r, "dt") for r in _pool("dt", date)]
    except Exception as e:  # noqa: BLE001
        notes.append(f"跌停池取不到：{str(e)[:80]}")

    # 概念题材温度
    concepts = []
    try:
        concepts = _concept_board()
    except Exception as e:  # noqa: BLE001
        notes.append(f"概念板块涨幅榜取不到：{str(e)[:80]}")

    # 热点题材榜（涨停家数聚合）
    themes = _themes(pool)

    # 龙头梯队：连板 >= 2，按「连板数 → 累计涨停数 → 封板时间」排序。
    # 连板数相同（都是 4 板）时，累计涨停数更多（如 9天5板 vs 4天4板）的妖股排前。
    dragon = sorted([r for r in pool if r["lbc"] >= 2],
                    key=lambda r: (-r["lbc"], -r["ct"], r["fbt"]))
    # 首板（跟风补涨首板）：连板 = 1
    first = sorted([r for r in pool if r["lbc"] == 1],
                   key=lambda r: (r["fbt"], -float(r.get("hs") or 0)))

    # 补涨候选（行业成分）
    catchup = []
    try:
        ind_map = _industry_map()
        catchup = _catchup(themes, pool, ind_map)
    except Exception as e:  # noqa: BLE001
        notes.append(f"补涨候选取不到（行业成分接口）：{str(e)[:80]}")

    # 买入候选 Top5（补涨 + 龙头 综合打分）
    buy = _buy_top5(themes, dragon, catchup)

    return {
        "as_of": date,
        "empty": False,
        "market": {
            "zt": len(pool),
            "zb": len(zb),
            "dt": len(dt_pool),
            "max_lbc": max((r["lbc"] for r in pool), default=0),
        },
        "concepts": concepts,
        "themes": themes,
        "dragon": dragon,
        "first": first,
        "zhaban": zb,
        "catchup": catchup,
        "buy": buy,
        "notes": notes,
    }
