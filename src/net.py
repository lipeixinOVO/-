# -*- coding: utf-8 -*-
"""带重试的 HTTP 抓取层（纯标准库）。"""
import time
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_LOG = []


def fetch(url, headers=None, enc="utf-8", retries=3, timeout=12):
    """返回解码后的文本；全部失败抛最后一个异常。"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            _LOG.append(("OK", url, len(raw)))
            return raw.decode(enc, errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            _LOG.append(("ERR", url, f"{type(e).__name__}: {e}"))
            if i < retries - 1:
                # 东财等接口遇到连发会直接断连，退避要够长
                time.sleep(2.0 + i * 3.0)
    raise last


def fetch_json(url, headers=None, retries=3, timeout=12):
    import json
    txt = fetch(url, headers=headers, retries=retries, timeout=timeout)
    return json.loads(txt)


def log_lines():
    return _LOG
