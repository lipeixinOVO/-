# -*- coding: utf-8 -*-
"""量各区块在给定视口宽度下的真实高度（给 content-visibility 的
contain-intrinsic-size 校准占位值，避免滚动跳动）。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import _chrome  # noqa: E402

SEL = ['.grid', '.notes', '.mchart', '.charthint', '.chartbar', '.chart', '.lab', '.foot']


def measure(width):
    wrap = os.path.join(ROOT, '_measure_wrap.html')
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>x</title>
<style>html,body{margin:0}</style></head>
<body><iframe id="f" src="docs/index.html" style="border:0;width:%dpx"></iframe>
<script>
document.getElementById('f').onload = function(){
  var doc = this.contentDocument;
  var self = this;
  this.style.height = doc.documentElement.scrollHeight + 'px';
  // 触发一遍滚动，让 content-visibility 的区块都真渲染过，量的才是真实高度
  var h = doc.documentElement.scrollHeight;
  var y = 0;
  var step = function(){
    y += 900; self.contentWindow.scrollTo(0, y);
    if(y < h){ setTimeout(step, 60); } else { setTimeout(done, 400); }
  };
    var done = function(){
    var doc = self.contentDocument;
    // 强制所有区块渲染，量到的才是真实高度（否则 content-visibility 给的是占位值）
    doc.head.insertAdjacentHTML('beforeend',
      '<style>.grid,.mchart,.charthint,.chartbar,.chart,.lab,.notes,.foot{content-visibility:visible !important}</style>');
    setTimeout(function(){
      var m = {};
      %s
      document.title = JSON.stringify(m);
    }, 600);
  };  setTimeout(step, 100);
};
</script></body></html>""" % (width,
        '\n    '.join(
            'var es = doc.querySelectorAll("%s"); for(var i=0;i<es.length;i++){ m["%s#"+i] = Math.round(es[i].getBoundingClientRect().height); }'
            % (s, s) for s in SEL))
    with open(wrap, 'w', encoding='utf-8') as f:
        f.write(html)
    out = _chrome.run([
        "--headless", "--allow-file-access-from-files", "--disable-web-security",
        "--window-size=%d,900" % width, "--virtual-time-budget=8000",
        "--dump-dom", "file:///" + wrap.replace("\\", "/")])
    if not isinstance(out, str):          # _chrome.run 返回 CompletedProcess
        out = out.stdout or b""
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    import re
    m = re.search(r"<title>(.*?)</title>", out, re.S)
    if m and m.group(1).strip().startswith('{'):
        return json.loads(m.group(1))
    print(out[:400])
    return None


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 390
    r = measure(w)
    if r:
        print("视口宽 %d：" % w)
        for k, v in sorted(r.items()):
            print("  %-12s %d px" % (k, v))
