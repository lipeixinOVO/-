# -*- coding: utf-8 -*-
"""CI 环境连通性探针：在 GitHub Runner 上逐个人试数据源，打印状态码与字节数。

用途：判断哪些源在云端可用，避免"本地能跑、上线全废"。
只在调试期挂在 workflow 里，稳定后可删。
"""
import sys
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

TARGETS = [
    # 名称, URL, Referer
    ("东财 沪深300 1.000300",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000300"
     "&fields1=f1,f2,f3&fields2=f51,f53,f56&klt=101&fqt=1&beg=0&end=20500101", ""),
    ("东财 中证红利 1.000922",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000922"
     "&fields1=f1,f2,f3&fields2=f51,f53,f56&klt=101&fqt=1&beg=0&end=20500101", ""),
    ("东财 COMEX 101.GC00Y",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=101.GC00Y"
     "&fields1=f1,f2,f3&fields2=f51,f53,f56&klt=101&fqt=1&beg=0&end=20500101", ""),
    ("东财 美元指数 100.UDI",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=100.UDI"
     "&fields1=f1,f2,f3&fields2=f51,f53&klt=101&fqt=1&beg=0&end=20500101", ""),
    ("东财 USDCNH 133.USDCNH",
     "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=133.USDCNH"
     "&fields1=f1,f2,f3&fields2=f51,f53&klt=101&fqt=1&beg=0&end=20500101", ""),
    ("新浪 A股日线 sh000300",
     "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
     "CN_MarketData.getKLineData?symbol=sh000300&scale=240&ma=no&datalen=3000",
     "https://finance.sina.com.cn"),
    ("腾讯日线 sh000300",
     "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000300,day,,,4000,qfq", ""),
    ("腾讯日线 sh000922",
     "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000922,day,,,4000,qfq", ""),
    ("新浪外盘期货 GC",
     "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_GC=/"
     "GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=GC",
     "https://finance.sina.com.cn"),
    ("中证指数 000922",
     "https://www.csindex.com.cn/csindex-home/perf/index-perf"
     "?indexCode=000922&startDate=2024-01-01&endDate=2030-01-01",
     "https://www.csindex.com.cn/"),
    ("蛋卷估值 NDX",
     "https://danjuanfunds.com/djapi/index_eva/detail/NDX", "https://danjuanfunds.com/"),
    ("美国财政部 real yield 2026",
     "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
     "daily_treasury_real_yield_curve/Text?data=daily_treasury_real_yield_curve"
     "&field_tdr_date_value=2026&type=datetime", ""),
    ("MSCI 106801",
     "https://app2.msci.com/products/service/index/indexmaster/getLevelDataForGraph"
     "?currency_symbol=USD&index_variant=NETR&start_date=20260901&end_date=20261022"
     "&data_frequency=DAILY&index_codes=106801",
     "https://www.msci.com/end-of-day-data-search"),
    ("Stooq 美元指数 dx.f",
     "https://stooq.com/q/d/l/?s=dx.f&i=d", ""),
    ("Stooq 黄金 xauusd",
     "https://stooq.com/q/d/l/?s=xauusd&i=d", ""),
]


def main():
    ok = 0
    for name, url, ref in TARGETS:
        h = {"User-Agent": UA}
        if ref:
            h["Referer"] = ref
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read()
            print(f"  OK  {r.status} {len(body):>7}B  {name}", flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}          {name}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ERR {type(e).__name__:<14}{name}  {str(e)[:70]}", flush=True)
    print(f"\n汇总：{ok}/{len(TARGETS)} 可用", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
