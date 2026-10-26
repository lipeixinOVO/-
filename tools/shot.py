# -*- coding: utf-8 -*-
"""本地截图：把 docs/index.html 塞进 iframe，把目标元素顶到视口顶端再拍。

Chrome headless 的 --screenshot 只拍视口，页面很长时抓不到下半部分；
`--window-size=390` 又会被最小窗口宽度顶到 ~497，看着像横向溢出（其实没有）。

两个坑都记一下：
  1. 滚动不能用 URL hash —— 站内大部分区块是 class 不是 id（.grid / .mchart），
     `index.html#mchart` 找不到元素就停在页首，截出来是完全无关的一段。
  2. 用 scrollTo 也不稳 —— --virtual-time-budget 下滚动常常在截图之后才生效。
     这里改成给 iframe 设**负 margin-top**（布局层面的位移，不是滚动状态），
     同时把 iframe 高度开到 4 倍视口，保证整页都已布局完。

用法：
    python tools/shot.py _shots/card-mobile.png ".card" 390 640
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import _chrome  # noqa: E402  （必须在 sys.path 注入之后）


def shot(out, sel, w, h, query=""):
    w, h = int(w), int(h)
    wrap = os.path.join(ROOT, "_shot_wrap.html")
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:#f7f5f1;overflow:hidden}
#vp{width:%dpx;height:%dpx;overflow:hidden;position:relative}
#f{border:0;display:block;width:%dpx;height:%dpx}</style></head><body>
<div id="vp"><iframe id="f" src="docs/index.html%s" scrolling="no"></iframe></div>
<script>
document.getElementById('f').onload = function(){
  var doc = this.contentDocument;
  var el = doc.querySelector(%s);
  if(!el) return;
  // 先把 iframe 拉到整页高度再量位置：原来高度写死成视口的 4 倍，
  // 目标区块在页面更下方时（分数历史图在 y≈2600）会定位到 iframe 之外，拍出一张纯背景色。
  this.style.height = (doc.documentElement.scrollHeight + 40) + 'px';
  var y = el.getBoundingClientRect().top + (this.contentWindow.scrollY || 0);
  this.style.marginTop = (-Math.max(0, y - 8)) + 'px';
};
</script>
</body></html>""" % (w, h, w, h * 4, query, json.dumps(sel))
    with open(wrap, "w", encoding="utf-8") as f:
        f.write(html)
    dst = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(dst) or ROOT, exist_ok=True)
    _chrome.run([
        # file:// 下每个文件都是独立 origin，父页拿不到 iframe.contentDocument ——
        # 上面那段定位脚本会静默失效，截出来永远是页首。这两个开关必加。
        "--allow-file-access-from-files",
        "--disable-web-security",
        "--force-device-scale-factor=2", "--window-size=%d,%d" % (w, h),
        "--virtual-time-budget=4000",
        "--screenshot=" + dst,
        "file:///" + wrap.replace("\\", "/")])
    print(out, os.path.getsize(dst) if os.path.exists(dst) else "MISSING")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit("用法：python tools/shot.py <输出png> <CSS选择器> <宽> <高> [?查询串]")
    shot(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
         sys.argv[5] if len(sys.argv) > 5 else "")
