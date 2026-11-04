# -*- coding: utf-8 -*-
"""端到端断言：content-visibility:auto 生效的前提下，JS 绘制的分数历史图
在滚动到位后真实存在（有 <svg>、有折线 path），首屏外区块都能落地渲染。"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import _chrome  # noqa: E402

wrap = os.path.join(ROOT, "_assert_wrap.html")
html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>x</title>
<style>html,body{margin:0}</style></head>
<body><iframe id="f" src="docs/index.html" style="border:0;width:390px"></iframe>
<script>
document.getElementById('f').onload = function(){
  var doc = this.contentDocument, self = this;
  this.style.height = doc.documentElement.scrollHeight + 'px';
  var chart = doc.getElementById('chart');
  chart.scrollIntoView();
  setTimeout(function(){
    var d = self.contentDocument;
    var m = {};
    m['chart_svg']   = d.querySelectorAll('#chart svg').length;
    m['chart_path']  = d.querySelectorAll('#chart path').length;
    m['chart_text']  = d.querySelectorAll('#chart text').length;
    m['grid_cards']  = d.querySelectorAll('#grid .card').length;
    m['mchart_svg']  = d.querySelectorAll('.mchart svg').length;
    m['lab_svg']     = d.querySelectorAll('.lab svg').length;
    m['live_cells']  = d.querySelectorAll('#live .cell').length;
    m['hero_cards']  = d.querySelectorAll('#hero > div').length;
    document.title = JSON.stringify(m);
  }, 1200);
};
</script></body></html>"""
with open(wrap, "w", encoding="utf-8") as f:
    f.write(html)
out = _chrome.run([
    "--headless", "--allow-file-access-from-files", "--disable-web-security",
    "--window-size=390,900", "--virtual-time-budget=10000",
    "--dump-dom", "file:///" + wrap.replace("\\", "/")])
if not isinstance(out, str):
    out = (out.stdout or b"").decode("utf-8", "replace")
m = re.search(r"<title>(.*?)</title>", out, re.S)
if not m:
    print(out[:500])
    sys.exit(1)
r = json.loads(m.group(1))
ok = True
checks = [
    ("chart_svg",  1,  "分数历史 SVG 生成"),
    ("chart_path", 5,  "折线 path（4标的线+50分基线，IXIC 不画）"),
    ("chart_text", 10, "坐标轴与标签文字"),
    ("grid_cards", 5,  "5 张评分卡"),
    ("mchart_svg", 1,  "近一月图 SVG"),
    ("lab_svg",    1,  "labs 区 SVG"),
    ("live_cells", 6,  "实时条 6 格"),
    ("hero_cards", 3,  "hero 三卡"),
]
print("== content-visibility 生效下的端到端断言（390 宽） ==")
for k, minv, desc in checks:
    v = r.get(k, 0)
    flag = "OK " if (v if isinstance(v, int) else 0) >= minv else "FAIL"
    if flag == "FAIL":
        ok = False
    print("  [%s] %-28s %s = %s (需≥%d)" % (flag, desc, k, v, minv))
print("断言结果：", "全部通过" if ok else "有失败项")
sys.exit(0 if ok else 1)
