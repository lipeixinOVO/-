# -*- coding: utf-8 -*-
"""本地截图：把 docs/index.html 塞进一个固定视口的 iframe，滚到指定元素再拍。

Chrome headless 的 --screenshot 只拍视口，页面很长时抓不到下半部分；
`--window-size=390` 又会被最小窗口宽度顶到 ~497，看着像横向溢出（其实没有）。
用 iframe 两个问题一起解决：视口宽高完全可控，锚点负责滚到目标位置。

用法：
    python tools/shot.py _shots/eq-desktop.png "#eqw" 1200 760
    python tools/shot.py _shots/eq-mobile.png   "#eqw"  390 640
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def shot(out, sel, w, h):
    w, h = int(w), int(h)
    wrap = os.path.join(ROOT, "_shot_wrap.html")
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:#f7f5f1;overflow:hidden}
iframe{border:0;display:block;width:%dpx;height:%dpx}</style></head><body>
<iframe id="f" src="docs/index.html#%s" scrolling="no"></iframe>
</body></html>""" % (w, h, sel.lstrip("#"))
    with open(wrap, "w", encoding="utf-8") as f:
        f.write(html)
    dst = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(dst) or ROOT, exist_ok=True)
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=2", "--window-size=%d,%d" % (w, h),
           "--virtual-time-budget=4000",
           "--user-data-dir=" + os.path.join(ROOT, "_shot_profile"),
           "--screenshot=" + dst,
           "file:///" + wrap.replace("\\", "/")]
    subprocess.run(cmd, check=False, capture_output=True)
    print(out, os.path.getsize(dst) if os.path.exists(dst) else "MISSING")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit("用法：python tools/shot.py <输出png> <#锚点> <宽> <高>")
    shot(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
