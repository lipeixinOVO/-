# -*- coding: utf-8 -*-
"""单独渲染页面里的某一个区块并截图（带原样式，不带其它内容）。

为什么不用「整页 + 滚动 + 视口截图」：
  headless Chrome 的 --screenshot 只拍视口，而 iframe 里 scrollTo 在
  --virtual-time-budget 下常常在截图之后才生效，截出来永远是页首。
  「把目标区块单独取出来、套上原 CSS 渲染」没有时序问题，图多高就多高。

用法：
    python tools/peek.py _shots/x.png "chart mchart" 1200
    python tools/peek.py _shots/y.png "grid" 1200
第二个参数是 class 串（用空格连），会匹配 class="..." 完全等于它的第一个 div。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import _chrome  # noqa: E402  （必须在 sys.path 注入之后）

DIV = re.compile(r"<(/?)div\b", re.I)


def extract(html, cls):
    """取出 class 完全等于 cls 的第一个 div 的完整 outerHTML（靠 <div> 计数配平）。"""
    m = re.search(r'<div class="%s"' % re.escape(cls), html)
    if not m:
        return ""
    start = m.start()
    depth, pos = 0, start
    while True:
        t = DIV.search(html, pos)
        if not t:
            return html[start:]
        depth += -1 if t.group(1) else 1
        pos = t.end()
        if depth == 0:
            return html[start:html.find(">", pos) + 1]


def peek(out, cls, w, h=3000, pad=20):
    w, h, pad = int(w), int(h), int(pad)
    src = os.path.join(ROOT, "docs", "index.html")
    html = open(src, encoding="utf-8").read()
    css = html[html.find("<style>") + 7: html.find("</style>")]
    seg = extract(html, cls)
    if not seg:
        raise SystemExit("没找到 class=%r 的区块" % cls)
    # 拼字符串而不是 %-格式化：原 CSS 里全是 100% / 50%，用 % 会当场炸
    page = ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + css + "</style>"
            "<style>html,body{margin:0;background:#f7f5f1}"
            "body{padding:" + str(pad) + "px;width:" + str(w) + "px;box-sizing:border-box}"
            "svg{max-width:100%}</style></head><body>" + seg + "</body></html>")
    tmp = os.path.join(ROOT, "_peek.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page)
    dst = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(dst) or ROOT, exist_ok=True)
    _chrome.run([
        "--force-device-scale-factor=2", "--window-size=%d,%d" % (w, h),
        "--virtual-time-budget=3000",
        "--screenshot=" + dst,
        "file:///" + tmp.replace("\\", "/")])
    print(out, os.path.getsize(dst) if os.path.exists(dst) else "MISSING")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("用法：python tools/peek.py <输出png> <class串> <宽> [高]")
    peek(sys.argv[1], sys.argv[2], sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else 3000)
