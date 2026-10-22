# -*- coding: utf-8 -*-
"""数据源封装。每个函数只负责"取到干净数据"，不做业务判断。

返回约定：时间序列统一为升序。
带磁盘缓存（默认 6 小时），避免调试时反复打接口被限流。
"""
import hashlib
import json
import os
import re
import time
import datetime as dt

from .net import fetch, fetch_json

SINA_H = {"Referer": "https://finance.sina.com.cn"}
FUND_H = {"Referer": "https://fund.eastmoney.com/"}
F10_H = {"Referer": "https://fundf10.eastmoney.com/"}
DJ_H = {"Referer": "https://danjuanfunds.com/"}
MSCI_H = {"Referer": "https://www.msci.com/end-of-day-data-search",
          "Accept": "application/json, text/plain, */*"}

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
CACHE_TTL = 6 * 3600


def _cached(key, fn):
    safe = re.sub(r"[^\w.\-]", "_", key)[:80]
    path = os.path.join(CACHE_DIR, safe + ".json")
    try:
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_TTL:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:  # noqa: BLE001
        pass
    val = fn()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(val, f, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        pass
    return val


# ---------------------------------------------------------------- 行情

def sina_us_daily(symbol):
    """新浪美股日线，历史可回溯到 2004 年。symbol 例：.IXIC / .NDX / .INX"""
    def _go():
        url = ("https://stock.finance.sina.com.cn/usstock/api/json_v2.php/"
               f"US_MinKService.getDailyK?symbol={symbol}&___qn=3")
        rows = json.loads(fetch(url, timeout=25))
        out = []
        for r in rows:
            try:
                out.append([r["d"], float(r["c"])])
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        return out
    return [tuple(x) for x in _cached(f"us_{symbol}", _go)]


MSCI_INDEX_CODES = {
    "106801": "MSCI World Health Care（全球医疗保健，官方 index code）",
    "990100": "MSCI World（全球发达市场宽基，用于相对比价基准）",
}


def msci_index(code, variant="NETR"):
    """MSCI 官方指数点位（日频，可回溯 1999 年）。

    variant：
        STRD = 价格指数（不含分红）
        NETR = 净总回报（扣预扣税后分红再投）← 与基金累计净值口径一致，趋势/回撤用它
        GRTR = 总回报
    """
    def _go():
        end = dt.date.today().strftime("%Y%m%d")
        url = ("https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"
               f"?currency_symbol=USD&index_variant={variant}&start_date=19980101"
               f"&end_date={end}&data_frequency=DAILY&index_codes={code}")
        js = fetch_json(url, headers=MSCI_H, timeout=45, retries=3)
        lv = ((js.get("indexes") or {}).get("INDEX_LEVELS")) or []
        out = []
        for r in lv:
            try:
                d = str(int(r["calc_date"]))
                out.append([f"{d[:4]}-{d[4:6]}-{d[6:8]}", float(r["level_eod"])])
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"MSCI {code}/{variant} 返回空")
        return out
    return [tuple(x) for x in _cached(f"msci_{code}_{variant}", _go)]


def em_kline(secid):
    """东财日线：[(date, close, amount)]。secid 例：1.000922 / 101.GC00Y"""
    def _go():
        # 部分标的（如美元指数）不支持 f56/f57 字段，服务端会直接断连 → 降级再试
        js = None
        for fields2 in ("f51,f53,f56,f57", "f51,f53"):
            url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
                   f"?secid={secid}&fields1=f1,f2,f3,f4,f5"
                   f"&fields2={fields2}&klt=101&fqt=1&beg=0&end=20500101")
            try:
                js = fetch_json(url, timeout=20, retries=2)
                if js.get("data"):
                    break
            except Exception:  # noqa: BLE001
                js = None
        if not js:
            raise RuntimeError(f"em_kline 无数据: {secid}")
        data = js.get("data") or {}
        out = []
        for line in data.get("klines") or []:
            p = line.split(",")
            if len(p) < 2:
                continue
            try:
                close = float(p[1])
                amt = float(p[3]) if len(p) > 3 and p[3] not in ("", "-") else 0.0
            except ValueError:
                continue
            out.append([p[0], close, amt])
        out.sort(key=lambda x: x[0])
        return out
    return [tuple(x) for x in _cached(f"em_{secid}", _go)]


def sina_snapshot(code, enc="gbk"):
    """新浪实时快照。支持 gb_* / hf_* / DINIW / fx_*"""
    return _cached(f"snap_{code}", lambda: _snapshot_raw(code, enc))


def _snapshot_raw(code, enc):
    txt = fetch(f"https://hq.sinajs.cn/list={code}", headers=SINA_H, enc=enc)
    m = re.search(r'="(.*)"', txt)
    if not m or not m.group(1).strip():
        return {}
    parts = m.group(1).split(",")

    def f(i):
        try:
            return float(parts[i])
        except (ValueError, IndexError):
            return None

    if code.startswith("gb_"):
        return {"name": parts[0], "price": f(1), "chg_pct": f(2),
                "time": parts[3] if len(parts) > 3 else "", "open": f(5),
                "high": f(6), "low": f(7), "w52_high": f(8), "w52_low": f(9)}
    if code.startswith("hf_"):
        return {"name": parts[13] if len(parts) > 13 else code, "price": f(0),
                "prev_close": f(7), "high": f(4), "low": f(5),
                "time": parts[6] if len(parts) > 6 else "",
                "date": parts[12] if len(parts) > 12 else ""}
    if code == "DINIW":
        return {"name": "美元指数", "price": f(1), "date": parts[10] if len(parts) > 10 else ""}
    if code.startswith("fx_"):
        return {"name": parts[9] if len(parts) > 9 else code, "price": f(1), "time": parts[0]}
    return {"raw": parts}


# ---------------------------------------------------------------- 估值（蛋卷）

def dj_detail(code):
    return _cached(f"dj_detail_{code}", lambda: (fetch_json(
        f"https://danjuanfunds.com/djapi/index_eva/detail/{code}", headers=DJ_H).get("data") or {}))


def dj_pe_history(code):
    """指数 PE 历史 [(YYYY-MM-DD, pe)]"""
    def _go():
        js = fetch_json(f"https://danjuanfunds.com/djapi/index_eva/pe_history/{code}?day=all", headers=DJ_H)
        rows = ((js.get("data") or {}).get("index_eva_pe_growths")) or []
        out = []
        for r in rows:
            try:
                d = dt.datetime.utcfromtimestamp(r["ts"] / 1000).strftime("%Y-%m-%d")
                out.append([d, float(r["pe"])])
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        return out
    return [tuple(x) for x in _cached(f"dj_pe_{code}", _go)]


# ---------------------------------------------------------------- 基金

def fund_nav_history(code):
    """基金全历史净值。返回 (unit, acc, meta)

    unit = 单位净值（真实买入价，但**分红/折算会造成跳降，不可用于趋势计算**）
    acc  = 累计净值（含分红再投资，连续，趋势/回撤/波动一律用它）
    """
    def _go():
        txt = fetch(f"https://fund.eastmoney.com/pingzhongdata/{code}.js", headers=FUND_H, timeout=25)

        def parse(var):
            m = re.search(var + r"\s*=\s*(\[.*?\])\s*;", txt, re.S)
            if not m:
                return []
            rows = json.loads(m.group(1))
            out = []
            for r in rows:
                try:
                    if r[1] is None:
                        continue
                    d = dt.datetime.fromtimestamp(r[0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
                    out.append([d, float(r[1])])
                except (KeyError, TypeError, ValueError):
                    continue
            out.sort(key=lambda x: x[0])
            return out

        meta = {}
        for key in ("fS_name", "fund_Rate", "fund_sourceRate"):
            mm = re.search(key + r'\s*=\s*"([^"]*)"', txt)
            if mm:
                meta[key] = mm.group(1)
        return {"unit": parse("Data_netWorthTrend"),
                "acc": parse("Data_ACWorthTrend"),
                "meta": meta}
    d = _cached(f"fundnav_{code}", _go)
    return ([tuple(x) for x in d["unit"]],
            [tuple(x) for x in d.get("acc") or []],
            d["meta"])


def fund_status(code):
    """申购状态 + 最新净值（注意 QDII 净值 T+1/T+2 公布）"""
    def _go():
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=2"
        js = fetch_json(url, headers=F10_H)
        lst = ((js.get("Data") or {}).get("LSJZList")) or []
        if not lst:
            return {}
        r = lst[0]
        return {"nav_date": r.get("FSRQ"), "nav": _fl(r.get("DWJZ")),
                "acc_nav": _fl(r.get("LJJZ")), "chg_pct": _fl(r.get("JZZZL")),
                "subscribe_status": r.get("SGZT"), "redeem_status": r.get("SHZT")}
    return _cached(f"fundstatus_{code}", _go)


def _fl(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 宏观

TREASURY_TYPES = {
    "real": "daily_treasury_real_yield_curve",
    "nominal": "daily_treasury_yield_curve",
}


def treasury_curve(kind, years):
    """美国财政部收益率曲线 CSV。返回 [(date, pct)]，升序。

    注意表头大小写不统一：实际收益率是 "10 YR"，名义是 "10 Yr"。
    """
    t = TREASURY_TYPES[kind]
    out = []
    for y in years:
        def _go(y=y, t=t):
            url = ("https://home.treasury.gov/resource-center/data-chart-center/"
                   f"interest-rates/daily-treasury-rates.csv/{y}/all"
                   f"?type={t}&field_tdr_date_value={y}&page&_format=csv")
            txt = fetch(url, timeout=20, retries=2)
            lines = [ln for ln in txt.splitlines() if ln.strip()]
            if not lines:
                return []
            header = [h.strip().strip('"') for h in lines[0].split(",")]
            idx = None
            for i, h in enumerate(header):
                if "10" in h and "yr" in h.lower():
                    idx = i
                    break
            if idx is None:
                return []
            rows = []
            for ln in lines[1:]:
                p = ln.split(",")
                if len(p) <= idx:
                    continue
                try:
                    d = dt.datetime.strptime(p[0].strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
                    rows.append([d, float(p[idx])])
                except ValueError:
                    continue
            return rows
        try:
            out.extend([tuple(x) for x in _cached(f"tsy_{kind}_{y}", _go)])
        except Exception:  # noqa: BLE001
            continue
    out.sort(key=lambda x: x[0])
    return out
