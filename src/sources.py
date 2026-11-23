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


def usixj_daily():
    """usIXJ（iShares 全球医疗保健 ETF）日线：[(date, close)]，升序。

    usIXJ 跟踪 S&P Global 1200 Health Care (Sector) Capped Index —— 正是广发
    全球医疗保健指数(000369)跟踪的「标普全球1200医疗保健指数」，用它做该标的
    的行情代理（指数官方点位需订阅，公开拿不到）。

    数据源两层：
      1. 种子 data/usixj_seed.json —— 本地用腾讯自选股 CLI 一次性导出的约 5 年
         （1200 根）历史快照，随仓库提交。腾讯公开 web 接口（web.ifzq.gtimg.cn）
         对美股 ETF 只回传最新 1 根、拿不到全历史，所以历史靠这份种子。
      2. 每日增量 —— 跑批时用腾讯 fqkline 拉最新一根，日期新于种子末尾就追加。
    两者合并后按日期去重升序。腾讯 fqkline 对美股 ETF 只回 1 根是已知限制，
    所以历史深度 = 种子长度 + 每日累积，不会突然变多。
    """
    seed_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "usixj_seed.json")

    def _go():
        merged = {}
        try:
            with open(seed_path, encoding="utf-8") as f:
                for x in json.load(f):
                    try:
                        merged[str(x[0])] = float(x[1])
                    except (IndexError, TypeError, ValueError):
                        continue
        except Exception:  # noqa: BLE001
            pass
        try:
            url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                   "?param=usIXJ,day,,,5,qfq")
            js = fetch_json(url, timeout=20, retries=2)
            d = (js.get("data") or {}).get("usIXJ") or {}
            for r in (d.get("day") or d.get("qfqday") or []):
                try:
                    # day 行 = [date, open, close, high, low, volume, ...]
                    merged[str(r[0])] = float(r[2])
                except (IndexError, TypeError, ValueError):
                    continue
        except Exception:  # noqa: BLE001
            pass
        out = [[d, c] for d, c in sorted(merged.items())]
        if not out:
            raise RuntimeError("usIXJ 无数据（种子空且腾讯 fqkline 未返回）")
        return out

    return [tuple(x) for x in _cached("usixj_daily", _go)]


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
    """东财日线：[(date, close, amount)]。secid 例：1.000922 / 101.GC00Y

    实测注意：这个接口对部分 secid（1.000922、101.GC00Y）会**间歇性直接断连**
    （RemoteDisconnected，不带任何响应），本地和 GitHub Runner 都会遇到。
    所以这里多轮重试，并且调用方必须准备兜底源，不能只依赖它。
    """
    def _parse(klines):
        out = []
        for line in klines:
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

    def _go():
        last = "未尝试"
        for fields2 in ("f51,f53,f56,f57", "f51,f53"):
            url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
                   f"?secid={secid}&fields1=f1,f2,f3,f4,f5"
                   f"&fields2={fields2}&klt=101&fqt=1&beg=0&end=20500101")
            for attempt in range(3):
                try:
                    js = fetch_json(url, timeout=20, retries=2)
                    klines = (js.get("data") or {}).get("klines") or []
                    if klines:
                        return _parse(klines)
                    last = "返回体里没有 klines"
                except Exception as e:  # noqa: BLE001
                    last = f"{type(e).__name__}: {e}"
                time.sleep(0.6 + attempt * 1.0)
        raise RuntimeError(f"em_kline 无数据: {secid}（{last[:80]}）")

    return [tuple(x) for x in _cached(f"em_{secid}", _go)]


def csindex_perf(code, start="2004-01-01"):
    """中证指数官网日线：[(date, close, amount)]。amount 由 tradingValue(亿元) 换算成元。

    注意 tradeDate 两种格式混用：早期 "2004-01-01"，近期 "20261022"，必须统一。
    """
    def _go():
        url = ("https://www.csindex.com.cn/csindex-home/perf/index-perf"
               f"?indexCode={code}&startDate={start}&endDate=2030-01-01")
        js = fetch_json(url, headers={"Referer": "https://www.csindex.com.cn/"},
                        timeout=30, retries=3)
        out = []
        for r in js.get("data") or []:
            d = str(r.get("tradeDate") or "").strip()
            if len(d) == 8 and d.isdigit():
                d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            c = r.get("close")
            if len(d) != 10 or c is None:
                continue
            try:
                amt = float(r.get("tradingValue") or 0) * 1e8    # 亿元 → 元
            except (TypeError, ValueError):
                amt = 0.0
            out.append([d, float(c), amt])
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"csindex 无数据: {code}")
        return out
    return [tuple(x) for x in _cached(f"csindex_{code}_{start}", _go)]


def sina_gold_daily(symbol="GC"):
    """新浪外盘期货日线（COMEX 黄金连续 = GC）：[(date, close, 0)]。

    接口返回 JSONP，外面包了一层 `var _GC=(...)`；volume 恒为 0，所以成交额维度不可用，
    调用方会自动退化成动量指标。历史约 10 年（2016 起），与东财逐日对齐过。
    """
    def _go():
        url = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
               f"var%20_{symbol}=/GlobalFuturesService.getGlobalFuturesDailyKLine"
               f"?symbol={symbol}")
        txt = fetch(url, headers=SINA_H, timeout=25, retries=3)
        m = re.search(r"\((\[.*\])\)", txt, re.S)
        rows = json.loads(m.group(1)) if m else []
        out = []
        for r in rows:
            try:
                out.append([r["date"], float(r["close"]), 0.0])
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"新浪期货无数据: {symbol}")
        return out
    return [tuple(x) for x in _cached(f"sinagold_{symbol}", _go)]


def sina_cn_daily(symbol):
    """新浪 A 股/指数日线：[(date, close, 0)]。symbol 例：sh000300。

    实测从 GitHub Runner 可访问（347KB 全量），是东财 A 股接口的可靠备用。
    只返回最近 datalen 根，够算 10 年分位。
    """
    def _go():
        url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               f"CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=3000")
        txt = fetch(url, headers=SINA_H, timeout=25, retries=3)
        rows = json.loads(txt) if txt.strip().startswith("[") else []
        out = []
        for r in rows:
            try:
                out.append([r["day"], float(r["close"]), 0.0])
            except (KeyError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"新浪A股日线无数据: {symbol}")
        return out
    return [tuple(x) for x in _cached(f"sinacn_{symbol}", _go)]


def tx_kline(secid):
    """腾讯财经日线兜底：[(date, close, 0)]。secid 例：1.000300 → sh000300。"""
    mkt, code = secid.split(".", 1)
    sym = {"1": "sh", "0": "sz"}.get(mkt)
    if not sym:
        raise RuntimeError(f"tx_kline 不支持的市场前缀: {secid}")
    sym += code
    def _go():
        url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
               f"?param={sym},day,,,4000,qfq")
        js = fetch_json(url, timeout=25, retries=3)
        d = (js.get("data") or {}).get(sym) or {}
        rows = d.get("qfqday") or d.get("day") or []
        out = []
        for r in rows:
            try:
                out.append([r[0], float(r[2]), 0.0])
            except (IndexError, TypeError, ValueError):
                continue
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"tx_kline 无数据: {sym}")
        return out
    return [tuple(x) for x in _cached(f"tx_{sym}", _go)]


def cn_ohlc(symbol):
    """A 股指数日 K（OHLC）：[(date, open, close, high, low)]。symbol 例：sz399001。

    两个源按顺序试（2026-11-23 补的新浪兜底）：
      1. 腾讯 fqkline（首选，字段顺序与 qt.gtimg.cn 实时快照的今开/收盘/最高/最低逐一核对过）。
         它的 day 行 = [date, open, close, high, low, volume, ...]。
      2. **新浪** CN_MarketData.getKLineData（`scale=240` 即日线）。
         加它是因为 2026-11-23 实测腾讯 web.ifzq.gtimg.cn 对所有 param 组合都回
         HTTP **501 + JS 反爬挑战页**（`window.btoa(...)` 跳转），四个指数的技术位图
         因此整块变空、而且 szkline.run() 是"单个失败就跳过"，页面上看不出来 ——
         属于静默降级，必须有兜底。
    新浪返回 day/open/high/low/close 是**字符串**，且字段顺序与我们的元组不同，注意别弄反。
    """
    def _tx():
        url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
               f"?param={symbol},day,,,2000,qfq")
        js = fetch_json(url, timeout=25, retries=3)
        d = (js.get("data") or {}).get(symbol) or {}
        rows = d.get("qfqday") or d.get("day") or []
        out = []
        for r in rows:
            try:
                out.append([r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4])])
            except (IndexError, TypeError, ValueError):
                continue
        return out

    def _sina():
        url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
               f"CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=2000")
        rows = json.loads(fetch(url, timeout=25, headers=SINA_H))
        out = []
        for r in rows or []:
            try:
                out.append([r["day"], float(r["open"]),
                            float(r["close"]), float(r["high"]), float(r["low"])])
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def _go():
        out = []
        try:
            out = _tx()
        except Exception:  # noqa: BLE001
            out = []
        if not out:
            out = _sina()
        out.sort(key=lambda x: x[0])
        if not out:
            raise RuntimeError(f"cn_ohlc 无数据: {symbol}（腾讯/新浪均失败）")
        return out
    return [tuple(x) for x in _cached(f"ohlc_{symbol}", _go)]


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


# ---------------------------------------------------------------- CNN 恐惧与贪婪

# CNN 官方分档。边界不是照抄网页，是从 251 天历史数据反推验证的：
# extreme fear 实测最高 24.77、fear 25.26~44.86、neutral 45.23~54.97、greed 56.20~71.17，
# 所以边界就是 24 / 44 / 55 / 75。（网上常见的 0-25/26-49/50/51-74 是旧版口径。）
FNG_ZONES = [
    (0, 24, "extreme fear", "极度恐惧", "#a8321f"),
    (25, 44, "fear", "恐惧", "#c2703c"),
    (45, 55, "neutral", "中性", "#8a8d96"),
    (56, 75, "greed", "贪婪", "#5f8f6a"),
    (76, 100, "extreme greed", "极度贪婪", "#2f7d54"),
]

# 返回体里 9 个 key，但 sp500/sp125、vix/vix_50 是同一指标的两个版本，取一个就够
FNG_PARTS = {
    "market_momentum_sp500": ("股价动能", "标普500 相对 125 日均线的偏离"),
    "stock_price_strength": ("股价强度", "纽交所创新高与创新低的股票数对比"),
    "stock_price_breadth": ("市场宽度", "上涨股与下跌股的成交量对比"),
    "put_call_options": ("看跌/看涨", "期权市场 5 日看跌看涨比率"),
    "market_volatility_vix": ("波动率", "VIX 相对其 50 日均线的位置"),
    "junk_bond_demand": ("垃圾债需求", "高收益债与国债的利差"),
    "safe_haven_demand": ("避险需求", "股票与国债近 20 日回报之差"),
}

_CNN_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def _cnn_get(path):
    """CNN 的 WAF 会拦 urllib，只能用 http.client 手写请求。

    踩过的三点（2026-10-24 实测）：
      1. urllib 把 header 名规范成 "User-agent"（大写 A 小写 g），大小写一变就判 bot → HTTP 418；
      2. urllib 默认追加 Accept-Encoding: identity，同样触发拦截；
      3. ssl.create_default_context() 对这个域名握手会超时，必须 set_ciphers("DEFAULT:@SECLEVEL=1")。
    满足这三条后稳定 200。别改成 net.fetch，会直接挂。
    """
    import http.client
    import ssl

    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    conn = http.client.HTTPSConnection("production.dataviz.cnn.io", 443,
                                       timeout=30, context=ctx)
    try:
        conn.putrequest("GET", path, skip_accept_encoding=True)
        conn.putheader("User-Agent", _CNN_UA)
        conn.putheader("Accept", "application/json, text/plain, */*")
        conn.putheader("Accept-Language", "en-US,en;q=0.9")
        conn.putheader("Referer", "https://www.cnn.com/")
        conn.putheader("Origin", "https://www.cnn.com")
        conn.putheader("Connection", "close")
        conn.endheaders()
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return json.loads(body)
    finally:
        conn.close()


def cnn_fear_greed():
    """CNN Business 恐惧与贪婪指数（Fear & Greed Index）。日频，美东收盘后更新。

    **纯展示，不参与打分**：它衡量的是美股情绪，不是估值；本站五个标的的分数口径
    一律是指数自身的估值/趋势/情绪/宏观四维，把 F&G 混进去会让口径变成大杂烩。
    """
    def _go():
        j = _cnn_get("/index/fearandgreed/graphdata")
        fg = j.get("fear_and_greed") or {}
        raw = fg.get("score")
        if raw is None:
            raise RuntimeError("返回体里没有 fear_and_greed.score")
        score = float(raw)

        rating = str(fg.get("rating") or "").strip().lower()
        # 优先用 CNN 自己给的 rating 定档（它是权威）；万一文案变了再按分数区间兜底
        zone = next((z for z in FNG_ZONES if z[2] == rating), None)
        if zone is None:
            zone = next((z for z in FNG_ZONES if z[0] <= score <= z[1]), FNG_ZONES[2])

        ts = str(fg.get("timestamp") or "")
        try:
            utc = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_cn = (utc + dt.timedelta(hours=8)).strftime("%Y-%m-%d")
        except ValueError:
            date_cn = ts[:10]

        def _f(k):
            v = fg.get(k)
            return round(float(v), 1) if v is not None else None

        parts = []
        for key, (nm, why) in FNG_PARTS.items():
            v = j.get(key) or {}
            if v.get("score") is None:
                continue
            parts.append({"name": nm, "why": why, "score": round(float(v["score"]), 1),
                          "rating": str(v.get("rating") or "").strip().lower()})

        hist = ((j.get("fear_and_greed_historical") or {}).get("data")) or []
        pts = []
        for p in hist:
            try:
                pts.append([int(p["x"]), round(float(p["y"]), 2)])
            except (KeyError, TypeError, ValueError):
                continue

        return {
            "score": round(score, 1),
            "rating": rating,
            "label": zone[3],
            "color": zone[4],
            "zone": [zone[0], zone[1]],
            "zones": [[z[0], z[1], z[3], z[4]] for z in FNG_ZONES],
            "date": date_cn,
            "ts": ts,
            "prev_close": _f("previous_close"),
            "prev_week": _f("previous_1_week"),
            "prev_month": _f("previous_1_month"),
            "prev_year": _f("previous_1_year"),
            "parts": parts,
            "history": pts,
            "source": "CNN Business Fear & Greed（production.dataviz.cnn.io）",
        }

    return _cached("cnn_fng", _go)


def vix_quote():
    """VIX 本体报价（CNBC quote API）。返回 dict，**不缓存** —— 实时数据必须每次现拉。

    2026-11-23 实测可用的那条路（此前"VIX 没有免费实时源"的结论要修正）：
      https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?symbols=.VIX&...

    三条关键属性，缺一不可：
      1. **不需要 Referer**。CBOE 的 cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json
         确实能返回数据（current_price 等字段很全），但它要求 Referer 必须来自 cboe.com，
         否则 403 —— 浏览器发不出这种 Referer，前端用不了。CNBC 不带 Referer 就是 200。
      2. **回 Access-Control-Allow-Origin: ***，浏览器 fetch 可以直连轮询。
      3. `realTime` 为 true，且 `last`/`last_time` 每次请求都在前进
         （实测同一分钟内 29.80 → 29.85，时间戳 06:13:01 → 06:15:01）。

    仍然拿不到的东西：腾讯 usVIX（僵尸数据，时间戳卡 2026-09-14、K 线整段 21.67）、
    Yahoo ^VIX（403）、stooq（JS 验证页）、新浪/东财/westock（无 VIX 本体）。
    **绝不拿 VIXY / VXX 期货 ETF 冒充 VIX** —— 那是带溢价的另一只标的。

    返回值：{"last", "chg", "chg_pct", "prev_close", "at", "real_time", "source"}
    """
    url = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
           "?symbols=.VIX&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1"
           "&output=json&events=1")
    j = json.loads(fetch(url, timeout=12))
    q = j["FormattedQuoteResult"]["FormattedQuote"][0]
    last = float(q["last"])
    prev = float(q["previous_day_closing"])
    chg = q.get("change")
    chg = (last - prev) if chg in (None, "") else float(chg)
    pct = q.get("change_pct")
    if pct in (None, ""):
        pct = (chg / prev * 100.0) if prev else None
    else:
        pct = float(str(pct).replace("%", ""))
    return {
        "last": round(last, 2),
        "chg": round(chg, 2),
        "chg_pct": None if pct is None else round(pct, 2),
        "prev_close": round(prev, 2),
        "at": q.get("last_time") or "",
        "at_short": q.get("last_timedate") or "",
        "mkt": q.get("curmktstatus") or "",
        "real_time": bool(q.get("realTime")),
        "source": "CNBC 报价（quote.cnbc.com，CORS 开放，前端每分钟直连）",
    }


def vix_daily():
    """CBOE 官方 VIX 历史日线（1990 起，EOD 收盘价）。返回 [[YYYY-MM-DD, close], ...] 升序。

    这条只负责**历史**（分位、分档占比、7 个窗口的走势）—— 它每天只多一行，
    拿来做实时是错的。实时报价走上面的 vix_quote()。

    为什么不用腾讯 usVIX 做历史：那条接口是**僵尸数据** —— 时间戳长期停在 2026-09-14、
    涨跌幅恒为 0、K 线是整段 21.67 的占位值。拿它当 VIX 会直接错 40%（实测同期 CBOE
    收盘 35.89）。CBOE 官方 CSV 是唯一拿到 1990 起完整历史的免费渠道。
    """
    def _go():
        url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
        txt = fetch(url, timeout=30)
        out = []
        for i, line in enumerate(txt.strip().split("\n")):
            if i == 0:                      # 表头 DATE,OPEN,HIGH,LOW,CLOSE
                continue
            p = line.split(",")
            if len(p) < 5:
                continue
            try:
                d = dt.datetime.strptime(p[0].strip(), "%m/%d/%Y").date().isoformat()
                c = float(p[4])
            except (ValueError, IndexError):
                continue
            if c > 0:
                out.append([d, round(c, 2)])
        if len(out) < 2500:
            raise RuntimeError(f"VIX 历史条数异常（{len(out)}）")
        out.sort(key=lambda x: x[0])
        return out

    return _cached("vix_daily", _go)
