# -*- coding: utf-8 -*-
"""生成 docs/index.html。

纯手写 HTML/CSS/JS + 内联 SVG，不引 CDN：
GitHub Pages 是静态托管，引外部图表库一旦被墙整页白屏，手绘 SVG 最稳。
数据由 Python 侧直接内联，前端零 fetch。

视觉：纯黑底 + 香槟金点缀，细发丝描边，无圆角堆叠，走「高级感」路线。
"""
import json
import re

# ---------------------------------------------------------------- 样式

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  color-scheme:light;   /* CSS 级再钉一次浅色主题：部分手机内核无视 meta，但吃 CSS */
  --bg:#f7f5f1; --bg-2:#f2f0eb;
  --card-a:#ffffff; --card-b:#fdfcf9;
  --line:rgba(20,22,27,.11); --line-2:rgba(20,22,27,.2);
  --txt:#14161b; --dim:#3d4048; --dim2:#5d6069; --dim3:#878a93;
  --gold:#9c782f; --gold-l:#6f5520; --gold-d:#c6a860;
  --ink:#66727e; --ok:#2f7d54; --hot:#b4452e;
  --r:14px;
}
html{background:var(--bg);-webkit-text-size-adjust:100%;overscroll-behavior-y:contain}
body{
  background:
    radial-gradient(1100px 520px at 50% -220px, rgba(198,168,96,.18), transparent 62%),
    radial-gradient(760px 420px at 88% 8%, rgba(120,150,190,.09), transparent 60%),
    #f7f5f1;
  color:var(--txt);min-height:100vh;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  font-size:14.5px;line-height:1.62;
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
  font-feature-settings:"tnum" 1,"ss01" 1;
}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}

/* ---------- 手机端减负：首屏外的大块先不布局不绘制 ----------
   content-visibility:auto = 视口外的区块跳过布局/绘制/内存占用，滚近了才渲染
   （Chrome 85+ / iOS Safari 18+ 生效，老内核直接忽略该属性、行为不变，零风险）。
   背景：283KB 单页 HTML 在手机上全量布局，内存吃紧时渲染进程被系统杀掉，
   浏览器自动整页重载，每次重载先白屏再画内容 —— 用户看到的就是
   「很卡 + 莫名自动刷新 + 黑白来回变」（2026-11-04 用户报障）。
   contain-intrinsic-size 只影响占位高度，宽度不受影响（renderChart 只读 innerWidth，安全）。
   占位值是 tools/measure_sections.py 在 390/1100 视口下量的真实高度——
   差得越远，滚动时区块「落地」的跳动越明显。auto 前缀 = 渲染过一次后
   浏览器记住真实尺寸，之后不再跳。 */
.grid{content-visibility:auto;contain-intrinsic-size:auto 2085px}
.mchart{content-visibility:auto;contain-intrinsic-size:auto 510px}
.charthint{content-visibility:auto;contain-intrinsic-size:auto 80px}
.chartbar{content-visibility:auto;contain-intrinsic-size:auto 115px}
.chart{content-visibility:auto;contain-intrinsic-size:auto 510px}
.lab{content-visibility:auto;contain-intrinsic-size:auto 390px}
.notes{content-visibility:auto;contain-intrinsic-size:auto 700px}
.foot{content-visibility:auto;contain-intrinsic-size:auto 121px}
@media (min-width:640px){
  .grid{contain-intrinsic-size:auto 1254px}
  .mchart{contain-intrinsic-size:auto 475px}
  .charthint{contain-intrinsic-size:auto 18px}
  .chartbar{contain-intrinsic-size:auto 27px}
  .chart{contain-intrinsic-size:auto 475px}
  .lab{contain-intrinsic-size:auto 430px}
  .foot{contain-intrinsic-size:auto 81px}
}
.wrap{max-width:1120px;margin:0 auto;padding:0 22px 96px}

/* ---------- 顶部标题 ---------- */
.hd{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;
  padding:34px 0 22px;border-bottom:1px solid var(--line)}
.hd .brand{display:flex;align-items:baseline;gap:14px}
.hd h1{font-size:27px;font-weight:600;letter-spacing:.16em;color:#0e1013}
.hd .en{font-size:9.5px;letter-spacing:.34em;color:#9c782f;
  text-transform:uppercase;padding-bottom:4px}
.hd .meta{font-size:11.5px;color:var(--dim2);text-align:right;line-height:1.95;letter-spacing:.02em}
.hd .meta b{color:var(--txt);font-weight:500}
/* 三种节奏要一眼分开：分数每交易日 6 次 / 实时价每 60 秒 / 静态信息。
   注意类名用 .rt 不能用 .live —— .live 是下面那条实时行情条的容器样式，
   meta 里挂上会让整行变成灰底圆角条（踩过）。 */
.hd .meta .ln{display:block}
.hd .meta .k{display:inline-block;min-width:4.4em;margin-right:6px;color:var(--dim3);letter-spacing:.06em}
.hd .meta .ln.rt .k{color:#2f7d54}
.hd .meta .ok{color:#2f7d54}
.hd .meta .warn{color:#b4452e;font-weight:600}
.hd .meta .idle{color:var(--dim3)}
/* 「下次 周一 08:07」被折成两行会读不通（周一 / 08:07 分居两行），整段锁住不换行 */
.hd .meta .nw{white-space:nowrap}
.hd .dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--gold);
  margin-right:6px;vertical-align:1px;box-shadow:0 0 0 3px rgba(156,120,47,.14)}
/* 页面开着不动时，后台跑批已经出新数据了 —— 这个条负责告诉用户，并给一个刷新按钮。
   只在 http(s) 下检测（file:// 的 fetch 会被同源策略拦掉）。 */
.newbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0 0;
  padding:10px 14px;border-radius:8px;border:1px solid rgba(47,125,84,.32);
  background:rgba(47,125,84,.07);font-size:12px;color:#2b5443;letter-spacing:.02em}
.newbar[hidden]{display:none}
.newbar b{font-weight:600;color:#1f4536}
.newbar button{font-family:inherit;font-size:11.5px;letter-spacing:.04em;padding:5px 13px;
  border-radius:16px;border:1px solid rgba(47,125,84,.45);background:var(--card-a);color:#2b5443;
  cursor:pointer;-webkit-tap-highlight-color:transparent}
.newbar button:hover{background:rgba(47,125,84,.08)}

/* ---------- 结论条 ---------- */
.hero{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin:26px 0 10px}
.hero>div{background:linear-gradient(180deg,var(--card-a),var(--card-b));padding:17px 20px 18px}
.hero .k{font-size:9.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--dim2)}
.hero .v{font-size:23px;font-weight:500;margin-top:7px;letter-spacing:-.01em;line-height:1.25}
.hero .v.pick{color:var(--gold-l)}
.hero .hint{font-size:11px;color:var(--dim2);margin-top:5px;letter-spacing:.02em}

/* ---------- 阈值提示（只标位置，不喊买卖） ---------- */
.sigs{display:flex;flex-direction:column;gap:8px;margin:14px 0 4px}
.sig{display:flex;align-items:flex-start;gap:12px;padding:11px 16px 12px;border-radius:10px;
  border:1px solid var(--line);background:linear-gradient(180deg,#fffdf8,#fdfaf4)}
.sig .tag{flex:none;font-size:9.5px;letter-spacing:.14em;padding:2.5px 8px;border-radius:4px;
  white-space:nowrap;margin-top:1px;border:1px solid rgba(156,120,47,.34);color:#8a6b25;
  background:rgba(156,120,47,.07)}
.sig .tx{font-size:12.5px;color:#14161b;line-height:1.72;min-width:0}
.sig .tx b{font-weight:600}
.sig .num{flex:none;margin-left:auto;font-size:14px;font-weight:600;color:#8a6b25;
  font-variant-numeric:tabular-nums;white-space:nowrap;padding-top:1px}
.sig.hi{border-color:rgba(180,69,46,.3);background:linear-gradient(180deg,#fff8f5,#fdf4f0)}
.sig.hi .tag{color:#b4452e;border-color:rgba(180,69,46,.36);background:rgba(180,69,46,.06)}
.sig.hi .num{color:#b4452e}
.sig.calm{background:linear-gradient(180deg,var(--card-a),var(--card-b))}
.sig.calm .tag{color:var(--dim2);border-color:var(--line-2);background:rgba(20,22,27,.025)}
.sig.calm .num{color:var(--dim);font-weight:500}
.sigrule{font-size:10.5px;color:var(--dim2);letter-spacing:.02em;line-height:1.95;margin:10px 2px 0}
@media(max-width:640px){.sig{flex-wrap:wrap}.sig .num{margin-left:0}}

/* ---------- 美股市场情绪（CNN 恐惧与贪婪）----------
   配色沿用 CNN 原版：红=恐惧、绿=贪婪。这跟 A 股"涨红跌绿"是两套语义，
   所以色条只表示"情绪温度"，不代表涨跌方向 —— 页面上靠「不参与打分」和区间文字说明。 */
.mood{display:grid;grid-template-columns:198px 1fr;margin:14px 0 0;
  background:linear-gradient(180deg,var(--card-a),var(--card-b));
  border:1px solid var(--line);border-radius:10px;overflow:hidden}
.mood .ml{padding:15px 17px 16px;border-right:1px solid var(--line)}
.mood .k{font-size:9.5px;letter-spacing:.16em;color:#6b6e78;text-transform:uppercase}
.mood .src{font-size:9.5px;color:var(--dim3);margin-top:4px;letter-spacing:.02em}
.mood .sc{font-size:38px;line-height:1;margin-top:13px;
  font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.mood .sc b{font-weight:500}
.mood .sc small{font-size:11px;color:var(--dim3);margin-left:2px;font-weight:400;letter-spacing:0}
.mood .lb{font-size:13.5px;font-weight:600;margin-top:7px;letter-spacing:.08em}
.mood .delta{font-size:10px;color:var(--dim3);margin-top:11px;line-height:1.75;
  font-variant-numeric:tabular-nums}
.mood .mr{padding:15px 17px 14px}
.mood .gauge{position:relative;margin:6px 0 4px}
.mood .gb{display:flex;height:9px;border-radius:5px;overflow:hidden}
.mood .gb i{display:block;height:100%}
.mood .gp{position:absolute;top:-5px;width:2px;height:19px;background:#14161b;
  border-radius:2px;transform:translateX(-1px)}
.mood .gp span{position:absolute;top:-15px;left:50%;transform:translateX(-50%);
  font-size:10px;font-weight:600;color:#14161b;background:var(--card-a);padding:0 3px;
  font-variant-numeric:tabular-nums}
.mood .gt{position:relative;height:13px;margin-top:6px;font-size:9px;color:var(--dim3);
  font-variant-numeric:tabular-nums}
.mood .gt span{position:absolute;top:0;transform:translateX(-50%);white-space:nowrap}
.mood .gt span:first-child{transform:none}
.mood .gt span:last-child{transform:translateX(-100%)}
.mood .zl{list-style:none;margin:11px 0 0;padding:0;display:grid;gap:5px;
  font-size:11.5px;line-height:1.6}
.mood .zl li{display:flex;gap:9px;color:var(--dim2);padding-left:11px;position:relative}
.mood .zl li::before{content:"";position:absolute;left:0;top:7px;width:4px;height:4px;
  border-radius:50%;background:currentColor;opacity:.3}
.mood .zl li.on{color:#14161b}
.mood .zl li.on::before{width:6px;height:6px;top:6px;opacity:1;background:var(--mc)}
.mood .zl b{flex:0 0 auto;font-weight:500;min-width:8.2em}
.mood .zl li.on b{font-weight:700}
.mood .zl em{font-style:normal;color:var(--dim3)}
.mood .zl li.on em{color:#3f434c}
.mood .drive{font-size:10px;color:var(--dim3);margin-top:10px;padding-top:9px;
  border-top:1px solid var(--line);letter-spacing:.02em;line-height:1.7}
.mood .drive b{color:#3f434c;font-weight:500;font-variant-numeric:tabular-nums}
/* 直连状态：刷新成功会变成"直连 CNN 刷新 20:03:12"，失败就停在初始文案，
   用户能看出"是在直连"还是"用的跑批快照" */
.mood .at{font-size:9.5px;color:#2f7d54;margin-top:8px;letter-spacing:.03em;
  display:flex;align-items:center;gap:5px;font-variant-numeric:tabular-nums}
.mood .at::before{content:"";width:4px;height:4px;border-radius:50%;background:currentColor;
  opacity:.85;flex:0 0 4px}
.mood .at.idle{color:var(--dim3)}
.mood .note{font-size:9.5px;color:var(--dim3);margin-top:9px;line-height:1.75;letter-spacing:.02em}
.mood .note b{color:#6b6e78;font-weight:500}
@media(max-width:720px){
  .mood{grid-template-columns:1fr}
  .mood .ml{border-right:0;border-bottom:1px solid var(--line);padding-bottom:13px}
  .mood .sc{font-size:32px;margin-top:9px;display:inline-block;margin-right:12px}
  .mood .lb{display:inline-block}
  .mood .zl{font-size:11px}
  .mood .zl b{min-width:0}
  .mood .zl li{flex-wrap:wrap;gap:1px 9px}
}

/* ---------- 宏观条 ---------- */
.macro{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:var(--r);
  overflow:hidden;margin:22px 0 4px}
.macro div{background:#fbfaf7;padding:12px 16px 13px}
.macro .k{font-size:9.5px;letter-spacing:.16em;color:#6b6e78;text-transform:uppercase}
.macro .v{font-size:16px;font-weight:500;margin-top:3px;color:#14161b}
.macro .v small{font-size:10px;color:var(--dim2);font-weight:400;margin-left:2px}

/* ---------- 标的卡 ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(346px,1fr));gap:14px;margin-top:18px}
.card{position:relative;background:linear-gradient(180deg,var(--card-a) 0%,var(--card-b) 100%);
  border:1px solid var(--line);border-radius:var(--r);padding:19px 20px 16px;
  box-shadow:0 1px 2px rgba(20,22,27,.04),0 14px 30px -22px rgba(20,22,27,.35);
  transition:border-color .22s ease,box-shadow .22s ease,transform .22s ease}
.card:hover{border-color:rgba(156,120,47,.45);transform:translateY(-2px);
  box-shadow:0 2px 4px rgba(20,22,27,.05),0 22px 42px -24px rgba(20,22,27,.4)}
.card.ref{opacity:.86}
.card.ref:hover{opacity:.96}
.card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.card .nm{font-size:14.5px;font-weight:550;line-height:1.4;letter-spacing:.01em;color:#0e1013}
.card .px{font-size:10.5px;color:var(--dim2);margin-top:4px;letter-spacing:.03em}
.card .tag{font-size:9px;padding:2.5px 7px;border-radius:3px;color:var(--dim2);
  border:1px solid var(--line-2);letter-spacing:.14em;text-transform:uppercase;white-space:nowrap}

.card .mid{display:flex;align-items:flex-end;gap:14px;margin:17px 0 15px}
/* 分数用纯色，不用渐变裁切（-webkit-background-clip:text 在部分手机内核里
   会把文字画成近乎透明的浅灰，实测微信/夸克上分数看不清） */
.score{font-size:42px;font-weight:400;line-height:.92;letter-spacing:-.02em;
  color:#0f1217;-webkit-text-fill-color:#0f1217;
  font-variant-numeric:tabular-nums}
.score small{font-size:11px;color:#5d6069;margin-left:4px;vertical-align:3px;
  -webkit-text-fill-color:#5d6069;letter-spacing:.06em}
.mult{font-size:21px;font-weight:500;padding:5px 12px;border-radius:7px;line-height:1.25;
  white-space:nowrap;letter-spacing:.01em}
.mult.up{background:linear-gradient(180deg,rgba(198,168,96,.3),rgba(198,168,96,.14));
  color:#6f5520;border:1px solid rgba(156,120,47,.45)}
.mult.base{background:rgba(20,22,27,.06);color:#2f333c;border:1px solid var(--line-2)}
.mult.down{background:rgba(20,22,27,.03);color:#6c7480;border:1px solid var(--line-2)}
.lbl{font-size:10.5px;color:var(--dim2);margin-left:auto;text-align:right;line-height:1.6;
  letter-spacing:.02em}

/* 档内位置 */
.band{margin-bottom:15px}
.band .track{height:3px;background:rgba(20,22,27,.1);border-radius:2px;position:relative;overflow:hidden}
.band .fill{height:100%;border-radius:2px;
  background:linear-gradient(90deg,var(--gold-d),var(--gold) 65%,var(--gold-l))}
.band .cap{display:flex;justify-content:space-between;font-size:9.5px;color:var(--dim3);
  margin-top:5px;letter-spacing:.1em;text-transform:uppercase}

/* 四维 */
.dims{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-bottom:13px}
.dim{font-size:11.5px}
.dim .r{display:flex;justify-content:space-between;color:var(--dim2);margin-bottom:4px;letter-spacing:.03em}
.dim .r b{color:#14161b;font-weight:500}
.dim .t{height:2.5px;background:rgba(20,22,27,.1);border-radius:2px;overflow:hidden}
.dim .f{height:100%;border-radius:2px;transition:width .3s ease}

/* 近一月走势（价格口径，和分数无关，所以单独一条带分隔线） */
.spark{margin:0 0 12px;padding-top:11px;border-top:1px solid var(--line)}
.spark .hh{display:flex;justify-content:space-between;align-items:baseline;gap:8px;
  font-size:9.5px;color:var(--dim3);letter-spacing:.1em;margin-bottom:5px}
.spark .hh .v{font-size:13px;font-weight:600;letter-spacing:0;
  font-variant-numeric:tabular-nums;margin-left:5px}
.spark .v.up{color:#b4452e}
.spark .v.dn{color:#2f7d54}
.spark .v.mid{color:var(--dim2)}
.spark svg{display:block;width:100%;height:52px}
.spark .ax{display:flex;justify-content:space-between;font-size:9px;color:var(--dim3);
  letter-spacing:.06em;margin-top:2px;font-variant-numeric:tabular-nums}

/* 底部 */
.fund{font-size:10.5px;color:var(--dim2);padding-top:12px;border-top:1px solid var(--line);
  display:flex;justify-content:space-between;gap:8px;align-items:center;letter-spacing:.02em}
.fund .code{color:#2f333c;font-family:ui-monospace,monospace;letter-spacing:.04em}
.st{font-size:9.5px;padding:1.5px 6px;border-radius:3px;white-space:nowrap;letter-spacing:.05em}
.st.ok{background:rgba(47,125,84,.1);color:var(--ok)}
.st.lim{background:rgba(156,120,47,.12);color:var(--gold)}
.st.no{background:rgba(180,69,46,.1);color:var(--hot)}

/* ---------- 区块标题 ---------- */
h2{font-size:12px;font-weight:500;margin:44px 0 14px;padding-bottom:11px;
  border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:12px;
  flex-wrap:wrap;letter-spacing:.2em;text-transform:uppercase;color:#14161b}
h2 small{font-size:10.5px;color:var(--dim3);font-weight:400;letter-spacing:.06em;text-transform:none}
/* 每个区块的「数据时效」徽章：一眼分清哪些是每分钟在动、哪些是跑批快照。
   类名别用 .live —— 那是实时行情条容器的样式，组合选择器也会被它的 background 污染。 */
h2 .fq{font-style:normal;font-size:9px;font-weight:400;letter-spacing:.08em;
  padding:2.5px 8px;border-radius:20px;border:1px solid rgba(20,22,27,.13);
  color:var(--dim3);white-space:nowrap;text-transform:none;margin-left:auto}
h2 .fq.rt{color:#2f7d54;border-color:rgba(47,125,84,.32);background:rgba(47,125,84,.05)}
h2 .fq.snap{color:#8a6b25;border-color:rgba(156,120,47,.3);background:rgba(156,120,47,.05)}
.fqmini{font-style:normal;font-size:8.5px;letter-spacing:.06em;color:var(--dim3);
  border:1px solid rgba(20,22,27,.12);border-radius:3px;padding:0 4px;margin-left:6px;
  vertical-align:1px;white-space:nowrap}

/* ---------- 分数方向说明条 ---------- */
.dirbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:14px 0 0;padding:11px 16px;
  border:1px solid rgba(156,120,47,.32);border-radius:10px;
  background:linear-gradient(90deg,rgba(198,168,96,.18),rgba(198,168,96,.04) 58%,transparent);
  font-size:12.5px;color:#14161b;letter-spacing:.01em}
.dirbar .tagk{flex:none;font-size:9.5px;letter-spacing:.14em;color:#6f5520;font-weight:600;
  border:1px solid rgba(156,120,47,.42);padding:2.5px 8px;border-radius:4px;background:rgba(198,168,96,.16)}
.dirbar b{font-weight:600;color:#0e1013}
.dirbar .arw{color:#8a6b25;font-weight:600}
.dirbar .q{color:var(--dim2)}
.dirbar .sep{color:rgba(20,22,27,.28)}

/* ---------- 实时行情条 ---------- */
/* 用 flex 而不是 grid：grid 的 auto-fit 在列数除不尽时会留一格灰底，看起来像少了个标的 */
.live{display:flex;flex-wrap:wrap;gap:1px;background:var(--line);border:1px solid var(--line);
  border-radius:var(--r);overflow:hidden;margin:14px 0 4px}
.live .cell{flex:1 1 150px;background:linear-gradient(180deg,var(--card-a),var(--card-b));
  padding:10px 14px 11px;min-width:0}
.live .nm{font-size:9.5px;color:var(--dim2);letter-spacing:.08em;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.live .nm i{font-style:normal;font-size:8.5px;color:#8a6b25;border:1px solid rgba(156,120,47,.3);
  border-radius:3px;padding:0 4px;margin-left:5px;letter-spacing:.06em}
.live .px{font-size:15px;font-weight:600;color:#0e1013;margin-top:3px;
  font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.live .ch{font-size:11px;font-weight:600;margin-left:7px;font-variant-numeric:tabular-nums}
.live .ch.up{color:#b4452e}
.live .ch.dn{color:#2f7d54}
.live .ch.mid{color:var(--dim2)}
.live .stamp{flex:1 1 100%;background:linear-gradient(180deg,var(--card-a),var(--card-b));
  padding:7px 14px 8px;font-size:10px;color:var(--dim2);letter-spacing:.03em;
  display:flex;justify-content:space-between;gap:3px 14px;flex-wrap:wrap}
/* 三段说明各占一行：默认 flex 会把前两段排在一行左右分开，读起来像两个不相干的东西 */
.live .stamp>span{flex:1 1 100%}
.live .stamp i.now{font-style:normal}
.live .stamp b{color:#14161b;font-weight:500}

/* ---------- 图表 ---------- */
.charthint{display:flex;gap:18px;flex-wrap:wrap;margin:0 2px 10px;font-size:11px;
  color:var(--dim2);letter-spacing:.02em}
.charthint span{display:inline-flex;align-items:center;gap:6px}
.charthint i{width:14px;height:2px;border-radius:2px;display:inline-block;background:currentColor;opacity:.55}
.charthint .up{color:#8a6b25}
.charthint .dn{color:#5d6069}
.chart{background:linear-gradient(180deg,var(--card-a),var(--card-b));border:1px solid var(--line);
  border-radius:var(--r);padding:20px 18px 16px}
.chart svg{width:100%;height:auto;display:block}
/* 图表工具条：窗口切换 + 「较上一期」差值（让每天的变化看得出来） */
.chartbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:2px 2px 11px}
.chartbar .btns{display:flex;gap:6px}
.chartbar button{font-family:inherit;font-size:11.5px;letter-spacing:.05em;padding:5px 14px;
  border-radius:20px;border:1px solid var(--line-2);background:transparent;color:#3d4048;
  cursor:pointer;transition:background .18s ease,border-color .18s ease,color .18s ease;
  white-space:nowrap;-webkit-tap-highlight-color:transparent}
.chartbar button:hover{border-color:var(--gold);color:var(--gold-l)}
.chartbar button.on{background:rgba(156,120,47,.14);border-color:var(--gold);color:#5c4519;font-weight:600}
.chartbar .delta{margin-left:auto;display:flex;align-items:center;gap:13px;font-size:10.5px;
  color:var(--dim2);letter-spacing:.04em;flex-wrap:wrap}
.chartbar .delta .lb{color:var(--dim3);letter-spacing:.1em}
.chartbar .dd{display:inline-flex;align-items:center;gap:5px}
.chartbar .dd i{width:9px;height:3px;border-radius:2px;display:inline-block}
.chartbar .dd b{font-weight:600;color:var(--txt);font-variant-numeric:tabular-nums}
.sw[hidden]{display:none}

/* ---------- 文字块 ---------- */
.tscroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
/* 手机上表宽超过屏幕，给一句提示，否则右边三列会被当成"没有" */
.swipehint{display:none;font-size:10.5px;color:var(--dim2);letter-spacing:.04em;
  margin:9px 2px 0;text-align:center}
.notes{background:linear-gradient(180deg,#fdfcf9,#f7f5f0);border:1px solid var(--line);
  border-radius:var(--r);padding:20px 22px;font-size:12.5px;color:var(--dim);
  line-height:1.95;letter-spacing:.01em}
.notes b{color:#0e1013;font-weight:600}
.notes li{margin-left:16px;margin-bottom:4px}
.notes code{background:rgba(20,22,27,.06);padding:1px 5px;border-radius:3px;font-size:11px;
  font-family:ui-monospace,monospace;color:#2f333c}
.notes .warnbox{border-left:2px solid var(--gold);padding-left:14px;margin:14px 0;
  color:#6b5a35;background:linear-gradient(90deg,rgba(198,168,96,.14),transparent 70%);
  padding-top:8px;padding-bottom:8px}

.foot{margin-top:48px;padding-top:20px;border-top:1px solid var(--line);
  font-size:10.5px;color:var(--dim3);line-height:1.9;letter-spacing:.04em}

/* ---------- 观察型模块（长期锚 / 二十二年） ---------- */
.labs{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.lab{background:linear-gradient(180deg,var(--card-a),var(--card-b));border:1px solid var(--line);
  border-radius:var(--r);padding:18px 20px 12px;
  box-shadow:0 1px 2px rgba(20,22,27,.04),0 14px 30px -22px rgba(20,22,27,.35)}
.lab .t{font-size:13.5px;font-weight:600;color:#0e1013;letter-spacing:.01em}
.lab .sub{font-size:10.5px;color:var(--dim2);margin-top:4px;line-height:1.65;letter-spacing:.01em}
.lab .big{font-size:32px;font-weight:400;letter-spacing:-.02em;color:#14161b;
  margin:13px 0 0;line-height:1.1;font-variant-numeric:tabular-nums}
.lab .big small{font-size:11px;color:var(--dim3);margin-left:6px;letter-spacing:.04em}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:10px 16px;margin:13px 0 10px}
.kv .c{border-top:1px solid var(--line);padding-top:8px}
.kv .k{font-size:9.5px;color:var(--dim2);letter-spacing:.06em;text-transform:uppercase}
.kv .v{font-size:13px;color:#14161b;margin-top:3px;font-variant-numeric:tabular-nums}
.kv .v i{font-style:normal;font-size:10.5px;margin-left:5px;letter-spacing:.02em}
.kv .v i.up{color:#b4452e}
.kv .v i.dn{color:#2f7d54}
.kv .v i.mid{color:var(--dim2)}
.lab svg{width:100%;height:auto;display:block;margin-top:8px}
.lab .cap{font-size:9.5px;color:var(--dim3);margin-top:6px;letter-spacing:.04em;line-height:1.7}

/* 二十二年：标题 + 两条线口径 + 年化数字 */
.chart .cap{font-size:10px;color:var(--dim3);margin-top:9px;letter-spacing:.03em;line-height:1.9}
.chart .cap b{color:#3f434c;font-weight:600}
.chart .cap code{background:rgba(20,22,27,.06);padding:1px 4px;border-radius:3px;
  font-family:ui-monospace,monospace;font-size:9.5px;color:#2f333c}
/* 近一月涨跌对比：图例 + 宽窄两份画布（同 .eqw 的理由，手机上一份固定宽画布会被缩糊） */
.mhead .t{font-size:13.5px;font-weight:600;color:#0e1013;letter-spacing:.01em}
.mhead .sub{font-size:10.5px;color:var(--dim2);margin-top:5px;line-height:1.85}
.mhead .sub b{font-weight:600;color:#3f434c}
/* 指数技术位：顶部「当前价 / 涨跌幅 / 压力 / 支撑」提示条 */
.szk-top{display:flex;gap:14px 30px;flex-wrap:wrap;align-items:baseline;
  margin:14px 0 12px;padding:13px 16px;border-radius:10px;border:1px solid var(--line);
  background:rgba(20,22,27,.025)}
.szk-top .lbl{font-size:11px;color:var(--dim2);letter-spacing:.04em;margin-right:7px}
.szk-top b{font-variant-numeric:tabular-nums;font-weight:600}
.szk-top .szk-now b{font-size:23px;color:#0e1013;letter-spacing:-.01em}
.szk-top .szk-now .rt{font-size:9px;letter-spacing:.08em;color:#2f7d54;
  border:1px solid rgba(47,125,84,.32);background:rgba(47,125,84,.06);
  padding:1.5px 6px;border-radius:4px;vertical-align:2px;margin-left:8px}
.szk-top .res b{color:#b4452e}
.szk-top .sup b{color:#2f7d54}
.szk-top .pct{font-size:12px;color:var(--dim2);margin-right:5px;font-variant-numeric:tabular-nums}
.szk-top .gap{font-size:11px;color:var(--dim3);font-variant-numeric:tabular-nums;margin-left:3px}
.szk-top .chg{font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;margin-left:9px}
.szk-top .chg.up{color:#b4452e}
.szk-top .chg.dn{color:#2f7d54}
.szk-top .chg.mid{color:var(--dim2)}
.mlegs{display:grid;grid-template-columns:repeat(auto-fill,minmax(292px,1fr));
  gap:8px 20px;margin:13px 0 8px;font-size:11px;color:var(--dim2)}
.mleg{display:flex;align-items:baseline;gap:6px;min-width:0}
.mleg i{width:13px;height:2.5px;border-radius:2px;display:inline-block;flex:0 0 13px;
  position:relative;top:-3px}
.mleg .n{font-style:normal;color:#3f434c;flex:0 1 auto;min-width:0}
.mleg b{font-weight:600;font-variant-numeric:tabular-nums;flex:0 0 auto}
.mleg b.up{color:#b4452e}
.mleg b.dn{color:#2f7d54}
.mleg em{font-style:normal;color:var(--dim3);font-size:10.5px;letter-spacing:.02em;flex:0 0 auto}
.mchart .v-w{display:block} .mchart .v-n{display:none}
.szk .v-w{display:block} .szk .v-n{display:none}
@media (max-width:760px){
  .mchart .v-w{display:none} .mchart .v-n{display:block}
  .szk .v-w{display:none} .szk .v-n{display:block}
  .mlegs{grid-template-columns:1fr;gap:4px;font-size:10.5px;margin:11px 0 6px}
  .mleg{line-height:1.5}
  .mleg em{font-size:10px}
  /* 页头三行在手机上会折行，标签改成行内短标签，别留 4.4em 的空档 */
  .hd .meta{font-size:10.5px;line-height:1.8;text-align:left}
  .hd .meta .k{min-width:0;margin-right:5px}
}
.eqhead{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;
  flex-wrap:wrap;margin-bottom:12px}
.eqhead .t{font-size:13.5px;font-weight:600;color:#0e1013;letter-spacing:.01em}
.eqhead .sub{font-size:10.5px;color:var(--dim2);margin-top:5px;line-height:1.8;letter-spacing:.01em}
.eqhead .sub b{font-weight:600;color:#3f434c}
.eqleg{display:inline-flex;align-items:center;gap:6px;margin-right:16px;white-space:nowrap}
.eqleg i{width:16px;height:2.5px;border-radius:2px;display:inline-block}
.eqnums{font-size:11px;color:var(--dim2);text-align:right;line-height:1.95;
  font-variant-numeric:tabular-nums}
.eqnums b{font-weight:600;font-size:13px}
.eqnums .r{color:var(--dim3);font-size:9.5px;letter-spacing:.1em;margin-bottom:2px}
/* 服务端画两份画布：宽屏用 1060 单位画布、窄屏用 430 —— 手机上字号不会被缩成 3px */
.eqw .v-w{display:block} .eqw .v-n{display:none}
@media (max-width:760px){
  .eqw .v-w{display:none} .eqw .v-n{display:block}
  .eqhead{align-items:flex-start}
  .eqnums{text-align:left;font-size:10.5px}
  .eqnums b{font-size:12.5px}
}

@media(max-width:760px){
  .labs{grid-template-columns:1fr}
}

@media(max-width:720px){
  .hero{grid-template-columns:1fr 1fr}
  .hero>div:first-child{grid-column:1/-1}
}
@media(max-width:560px){
  .wrap{padding:0 15px 64px}
  .grid{grid-template-columns:1fr}
  /* 区块标题 + 时效徽章：手机上放不下一行就换行，别把徽章挤出屏幕 */
  h2{flex-wrap:wrap;gap:6px 10px;letter-spacing:.14em}
  h2 small{font-size:9.5px;letter-spacing:.02em}
  h2 .fq{font-size:8.5px;padding:2px 7px;margin-left:0}
  /* 5 个宏观格子排 2 列时最后一行会空一格，露出容器的灰底像块脏斑 → 让末格跨满。
     :nth-child(odd) 是为了只在「奇数个格子」时才跨，偶数个正好填满不用管。 */
  .macro>div:last-child:nth-child(odd){grid-column:1/-1}
  /* 手机上分数是主角：字号别缩太小，字重加粗，纯色不透明 */
  .score{font-size:40px;font-weight:500;color:#0b0e12;-webkit-text-fill-color:#0b0e12}
  .score small{font-size:12px;color:#4a4d56;-webkit-text-fill-color:#4a4d56}
  .mult{font-size:19px}
  .hd h1{font-size:21px;letter-spacing:.1em}
  .hd{padding-top:26px}
  /* 参考卡不要压透明度，手机上本来字就小，再淡就糊了 */
  .card.ref{opacity:1;border-style:dashed}
  /* 小字整体提一档对比度 */
  .card{padding:17px 16px 14px}
  .card .nm{font-size:15px}
  .card .px{color:#4a4d56}
  .dim{font-size:12px}
  .dim .r{color:#4a4d56}
  .dim .r b{color:#0e1013}
  .band .cap{font-size:10px;color:#6e717a}
  .lbl{color:#4a4d56}
  .fund{color:#4a4d56}
  .fund .code{color:#1a1d24}
  .macro .k{color:#5d6069}
  .macro .v{font-size:15px}
  .hd .meta{font-size:11px;color:#4a4d56}
  h2 small{color:#6e717a}
  .notes{font-size:12px;color:#3d4048}
  .notes code{color:#2f333c}
  .sig .tx{font-size:12.5px}
  /* 实时行情与图表工具条：手机上要能一眼看清、手指点得中 */
  .live .cell{flex:1 1 46%;padding:9px 12px 10px}
  .live .px{font-size:16px}
  .live .nm{font-size:10px;color:#4a4d56}
  .dirbar{font-size:12px;padding:10px 13px;gap:8px}
  .dirbar .sep{display:none}
  .tscroll table{min-width:540px}
  .swipehint{display:block}
  .chartbar{gap:8px}
  .chartbar button{font-size:12.5px;padding:6px 15px}
  /* 二十二年 / 深证成指的多窗口按钮要在一行里排开，手机上把内边距收紧 */
  .eqw .chartbar button,.szk .chartbar button{font-size:11.5px;padding:5px 9px;letter-spacing:.02em}
  .eqw .chartbar .delta,.szk .chartbar .delta{margin-left:0;font-size:10px}
  .charthint{font-size:11.5px;gap:12px}
}

/* ---------- 超短线擒龙（纯展示 · 不参与打分） ----------
   配色沿用 A 股「涨红跌绿」：涨停/涨幅=红、跌停=绿；炸板/异动用琥珀色单独标出，
   避免和「跌」混淆。板块本身是日频数据（涨停板池），标题右侧标「日频/随跑批刷新」。 */
.zl{content-visibility:auto;contain-intrinsic-size:auto 2600px}
.zl .zl-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0 12px}
.zl .zl-stats .st{background:linear-gradient(180deg,var(--card-a),var(--card-b));
  border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.zl .zl-stats .lbl{font-size:10px;letter-spacing:.12em;color:var(--dim2)}
.zl .zl-stats b{display:block;font-size:23px;font-weight:600;margin-top:4px;
  font-variant-numeric:tabular-nums;color:#0e1013}
.zl .zl-stats b.up{color:#b4452e}
.zl .zl-stats b.dn{color:#2f7d54}
.zl-tags{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin:2px 0 6px}
.zl-tags .tagk{font-size:10px;letter-spacing:.12em;color:var(--dim3);margin-right:4px}
.zl-tags .chip{font-size:11px;padding:2.5px 10px;border-radius:14px;border:1px solid var(--line);
  background:var(--card-a);color:var(--dim);font-variant-numeric:tabular-nums}
.zl-tags .chip b{font-weight:600;color:#b4452e}
.zl-at{font-size:9px;letter-spacing:.06em;color:#2f7d54;border:1px solid rgba(47,125,84,.32);
  background:rgba(47,125,84,.05);padding:1.5px 6px;border-radius:4px;margin-left:8px;white-space:nowrap}
.zl-at.idle{color:var(--dim3);border-color:var(--line-2);background:rgba(20,22,27,.03)}
.zl-at.warn{color:#8a6b25;border-color:rgba(156,120,47,.4);background:rgba(156,120,47,.08)}
.zl-ct{font-size:11.5px;font-weight:600;color:#0e1013;letter-spacing:.04em;margin:18px 0 8px;
  display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.zl-ct .hint{font-weight:400;color:var(--dim3);font-size:10px;letter-spacing:.02em}
.zl-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.zl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.zl-tbl{width:100%;border-collapse:collapse;font-size:11.5px}
.zl-tbl th{font-size:9.5px;color:var(--dim3);font-weight:400;text-align:left;letter-spacing:.08em;
  padding:0 8px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
.zl-tbl th.r{text-align:right}
.zl-tbl td{padding:6px 8px;border-bottom:1px solid var(--line);color:var(--txt);white-space:nowrap}
.zl-tbl tr:last-child td{border-bottom:0}
.zl-tbl .nm{font-weight:500;color:#14161b}
.zl-tbl .cd{color:var(--dim3);font-size:10px}
.zl-tbl .r{text-align:right;font-variant-numeric:tabular-nums}
.zl-tbl .up{color:#b4452e;font-weight:500}
.zl-tbl .dn{color:#2f7d54;font-weight:500}
.zl-tbl .dim{color:var(--dim2)}
.zl-badge{display:inline-block;font-size:10px;padding:1px 7px;border-radius:4px;line-height:1.7;
  border:1px solid rgba(180,69,46,.32);background:rgba(180,69,46,.07);color:#b4452e;white-space:nowrap;
  font-variant-numeric:tabular-nums}
.zl-badge.gold{border-color:rgba(156,120,47,.34);background:rgba(156,120,47,.08);color:#8a6b25}
.zl-badge.cycle{border-color:var(--line-2);background:rgba(20,22,27,.04);color:var(--dim2)}
.zl-badge.zb{border-color:rgba(156,120,47,.4);background:rgba(156,120,47,.1);color:#8a6b25}
.zl-zb-note{font-size:10px;color:var(--dim2);margin:2px 0 0;letter-spacing:.02em;line-height:1.7}
/* 按题材分组 · 领涨/补涨龙头卡（精简到每题材最强的两只） */
.zl-picks{margin:14px 0 10px}
.zl-picks .hd{font-size:11.5px;font-weight:600;color:#0e1013;letter-spacing:.04em;margin-bottom:10px;
  display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.zl-picks .hd .hint{font-weight:400;color:var(--dim3);font-size:10px;letter-spacing:.02em}
.zp-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.zp-card{background:linear-gradient(180deg,var(--card-a),var(--card-b));
  border:1px solid var(--line);border-radius:12px;padding:12px 13px 11px;min-width:0}
.zp-hd{font-size:13px;font-weight:700;color:#14161b;display:flex;align-items:baseline;gap:8px;
  margin-bottom:10px;padding-bottom:9px;border-bottom:1px solid var(--line)}
.zp-cnt{font-size:10px;font-weight:600;color:#b4452e;background:rgba(180,69,46,.08);
  border:1px solid rgba(180,69,46,.28);padding:1px 8px;border-radius:10px;margin-left:auto;
  white-space:nowrap}
.zp-row{position:relative;display:flex;align-items:flex-start;gap:9px;padding:8px 9px;
  border-radius:9px;margin-top:7px;border:1px solid transparent}
.zp-row+.zp-row{margin-top:4px}
.zp-row.buyable{background:linear-gradient(180deg,#fdf3f1,#fbeae5);border-color:rgba(180,69,46,.4)}
.zp-row.empty{color:var(--dim3)}
.zp-none{font-size:10px;color:var(--dim3);line-height:1.6}
.zp-role{flex:none;font-size:9.5px;font-weight:600;letter-spacing:.04em;padding:2px 7px;border-radius:5px;
  margin-top:1px;white-space:nowrap;font-variant-numeric:tabular-nums}
.zp-role.lead{border:1px solid rgba(180,69,46,.4);background:rgba(180,69,46,.1);color:#b4452e}
.zp-role.cu{border:1px solid rgba(156,120,47,.4);background:rgba(156,120,47,.1);color:#8a6b25}
.zp-info{flex:1;min-width:0}
.zp-nm{font-size:12.5px;font-weight:600;color:#14161b;line-height:1.3}
.zp-cd{font-size:10px;color:var(--dim3);font-weight:400;margin-left:4px}
.zp-meta{font-size:10px;color:var(--dim2);margin-top:4px;line-height:1.6;font-variant-numeric:tabular-nums}
.zp-meta .up{color:#b4452e;font-weight:600}
.zp-rs{font-size:10px;color:var(--dim3);margin-top:4px;line-height:1.5}
/* 可买：大大的红色「买」字圆标 */
.zp-buy-tag{flex:none;align-self:center;width:42px;height:42px;border-radius:50%;
  background:#c0392b;color:#fff;font-size:21px;font-weight:700;line-height:1;
  display:flex;align-items:center;justify-content:center;margin-left:6px;
  box-shadow:0 2px 9px rgba(192,57,43,.38)}
/* 可信度徽章（题材卡内复用）：高=暖红 · 中=琥珀金 · 低=灰 */
.zl-picks .cf{display:inline-block;font-size:9px;padding:1px 6px;border-radius:4px;margin-left:5px;
  vertical-align:middle;border:1px solid var(--line-2);background:rgba(20,22,27,.04);color:var(--dim3)}
.zl-picks .cf-hi{border-color:rgba(180,69,46,.32);background:rgba(180,69,46,.07);color:#b4452e}
.zl-picks .cf-mid{border-color:rgba(156,120,47,.34);background:rgba(156,120,47,.08);color:#8a6b25}
.zl-picks .cf-lo{border-color:var(--line-2);background:rgba(20,22,27,.04);color:var(--dim3)}
.zl-method{background:linear-gradient(180deg,#fdfcf9,#f7f5f0);border:1px solid var(--line);
  border-radius:10px;padding:14px 16px;margin-top:18px}
.zl-method .t{font-size:11.5px;font-weight:600;color:#0e1013;letter-spacing:.04em}
.zl-method ol{margin:8px 0 0 18px}
.zl-method li{font-size:11px;color:var(--dim);line-height:1.85;margin-bottom:5px}
.zl-method li b{color:#14161b;font-weight:600}
.zl-method .case{font-size:10.5px;color:var(--dim2);line-height:1.8;margin-top:6px}
.zl-method .case b{color:#3f434c}
@media(max-width:760px){
  .zl-grid{grid-template-columns:1fr}
  .zl .zl-stats{grid-template-columns:repeat(2,1fr);gap:8px}
  .zl-tbl{font-size:11px}
  .zl-tbl th,.zl-tbl td{padding-left:5px;padding-right:5px}
  .zp-grid{grid-template-columns:1fr}
  .zp-buy-tag{width:38px;height:38px;font-size:19px}
}
"""

JS = """
const P = window.__DATA__;
function fmtPx(v){ if(v==null) return '—';
  return Math.abs(v)>=100 ? v.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})
                          : v.toFixed(4); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
/* 文字宽度粗估（CJK 1em / ASCII 0.55em）。分数历史图是前端画的，只能在浏览器里算；
   只用来决定「右侧留白留多少」「名字要不要截断」，估大一点安全（留白多点不会溢出）。 */
function tw(s, fs){
  s = String(s==null?'':s);
  var w = 0;
  for(var i=0;i<s.length;i++){ w += s.charCodeAt(i) > 0x2E80 ? 1 : 0.55; }
  return w * fs;
}
/* 图上标签用的名字：去掉括号里的补充说明（黄金（COMEX 主力连续）→ 黄金）。 */
function cname(s){
  var t = String(s==null?'':s).replace(/[（(][^）)]*[）)]/g, '').replace(/ +/g, ' ').trim();
  return t || String(s==null?'':s);
}
/* 名字超出可用宽度就截断加省略号 —— 宁可少两个字，也不能顶出 viewBox 被裁掉。 */
function ellip(s, fs, maxw){
  s = String(s==null?'':s);
  if(tw(s, fs) <= maxw) return s;
  var out = '';
  for(var i=0;i<s.length;i++){
    if(tw(out + s.charAt(i), fs) > maxw - tw('…', fs)) break;
    out += s.charAt(i);
  }
  return (out || s.charAt(0)) + '…';
}
function multCls(m){ return m>1.02?'up':(m<0.98?'down':'base'); }
function stCls(s){ s=s||'';
  if(s.indexOf('暂停')>=0) return 'no';
  if(s.indexOf('限')>=0) return 'lim';
  if(s.indexOf('开放')>=0) return 'ok';
  return ''; }
function dimColor(sc){
  // 分数越高越该买 → 亮金；越低 → 冷灰。同一套色系里做明度区分，不用花花绿绿。
  if(sc>=65) return 'linear-gradient(90deg,#8a6b25,#c9a44e)';
  if(sc>=50) return 'linear-gradient(90deg,#9c7c42,#c6b184)';
  if(sc>=35) return 'linear-gradient(90deg,#7f8b9a,#aab4c1)';
  return 'linear-gradient(90deg,#a4a7b0,#c6c9cf)';
}
// 近一月涨跌走势条。涨红跌绿（A 股习惯，和分数配色无关）。
// 用 SVG 串进 innerHTML 而不是 canvas：卡片本来就是这个方式拼的，
// 而且 vector-effect 能让线宽在任意卡宽下都稳稳 1.5px，不被横向拉伸带粗。
// 近 7 天那一段用更粗的实线压在淡色全段之上，起点再画一根竖虚线 → 一眼看出"这一截是最近一周"。
function sparkSvg(m, key){
  if(!m || !m.pts || m.pts.length < 4) return '';
  var W = 320, H = 52, PX = 1, PY = 6;
  var vs = m.pts.map(function(p){ return p[1]; });
  var mn = Math.min.apply(null, vs), mx = Math.max.apply(null, vs);
  // 平盘时给一个最小幅度：否则一条直线贴着顶边，看着像没渲染出来
  if(mx - mn < 1.2){ var c0 = (mx + mn) / 2; mn = c0 - 0.6; mx = c0 + 0.6; }
  var pad = (mx - mn) * 0.12, lo = mn - pad, hi = mx + pad;
  var n = m.pts.length;
  var X = function(i){ return PX + (W - 2 * PX) * i / (n - 1); };
  var Y = function(v){ return PY + (H - 2 * PY) * (1 - (v - lo) / (hi - lo)); };
  var col = m.chg_month >= 0 ? '#b4452e' : '#2f7d54';
  var gid = 'sg-' + key;
  var line = '';
  m.pts.forEach(function(p, i){
    line += (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(p[1]).toFixed(1) + ' ';
  });
  var area = line + 'L' + X(n - 1).toFixed(1) + ' ' + (H - PY) + ' L' + X(0).toFixed(1) + ' ' + (H - PY) + ' Z';
  var i7 = 0;
  for(var i = 0; i < n; i++){ if(m.pts[i][0] === m.week_from){ i7 = i; break; } }
  var w7 = '';
  for(var j = i7; j < n; j++){
    w7 += (j === i7 ? 'M' : 'L') + X(j).toFixed(1) + ' ' + Y(m.pts[j][1]).toFixed(1) + ' ';
  }
  var NS = ' vector-effect="non-scaling-stroke"';
  var o = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none">';
  o += '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
       '<stop offset="0%" stop-color="' + col + '" stop-opacity=".24"/>' +
       '<stop offset="100%" stop-color="' + col + '" stop-opacity="0"/></linearGradient></defs>';
  o += '<path d="' + area + '" fill="url(#' + gid + ')"/>';
  if(0 > lo && 0 < hi){
    o += '<line x1="0" y1="' + Y(0).toFixed(1) + '" x2="' + W + '" y2="' + Y(0).toFixed(1) +
         '" stroke="rgba(20,22,27,.24)" stroke-width="1" stroke-dasharray="3 4"' + NS + '/>';
  }
  o += '<path d="' + line + '" fill="none" stroke="' + col + '" stroke-opacity=".62" stroke-width="1.5" ' +
       'stroke-linejoin="round" stroke-linecap="round"' + NS + '/>';
  if(i7 < n - 1){
    o += '<line x1="' + X(i7).toFixed(1) + '" y1="' + PY + '" x2="' + X(i7).toFixed(1) +
         '" y2="' + (H - PY) + '" stroke="rgba(20,22,27,.16)" stroke-width="1" stroke-dasharray="2 3"' + NS + '/>';
  }
  o += '<path d="' + w7 + '" fill="none" stroke="' + col + '" stroke-width="2.2" ' +
       'stroke-linejoin="round" stroke-linecap="round"' + NS + '/>';
  // 末点：用一条零长度 + 圆头描边的路径代替 circle（circle 会被横向拉伸成椭圆）
  o += '<path d="M' + X(n - 1).toFixed(1) + ' ' + Y(m.pts[n - 1][1]).toFixed(1) + ' l0 0" ' +
       'stroke="' + col + '" stroke-width="5" stroke-linecap="round"' + NS + '/>';
  return o + '</svg>';
}

function sparkBlock(a){
  var m = a.month;
  if(!m || !m.pts || m.pts.length < 4) return '';
  var cls = function(v){ return v > 0 ? 'up' : (v < 0 ? 'dn' : 'mid'); };
  var fmt = function(v){ return v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(2) + '%'; };
  var mm = function(d){ return String(d || '').slice(5); };      // 2026-10-22 → 10-22
  return '<div class="spark"><div class="hh">' +
    '<span>近一月涨跌<b class="v ' + cls(m.chg_month) + '">' + fmt(m.chg_month) + '</b></span>' +
    '<span>近 7 天<b class="v ' + cls(m.chg_week) + '">' + fmt(m.chg_week) + '</b></span>' +
    '</div>' + sparkSvg(m, a.id) +
    '<div class="ax"><span>' + mm(m.base_date) + ' 起</span><span>' + mm(m.end_date) + ' 止</span></div>' +
    '</div>';
}

/* ---------- 跑批时刻表（P.schedule，来源是 workflow 的 cron） ----------
   页面顶部要回答一个问题：「现在这个数据是正常节奏，还是卡住了？」
   只看「几小时前」会误判 —— 周五 15:17 到周六 08:07 本来就有 17 小时空档，
   那是休市不是故障。所以拿 workflow 里的 cron 算出「上一次计划时刻」来对照。 */
function schedSpan(S){
  if(!S || !S.runs || !S.runs.length) return null;
  var now = new Date(), prev = null, next = null;
  for(var off = -8; off <= 8; off++){
    var base = new Date(now.getFullYear(), now.getMonth(), now.getDate() + off);
    var dw = base.getDay() === 0 ? 7 : base.getDay();     // JS 0=周日 → 统一成 7
    for(var i = 0; i < S.runs.length; i++){
      if(S.runs[i][0] !== dw) continue;
      var hm = String(S.runs[i][1]).split(':');
      var t = new Date(base.getFullYear(), base.getMonth(), base.getDate(), +hm[0], +hm[1], 0);
      if(t.getTime() <= now.getTime()){ if(!prev || t > prev) prev = t; }
      else { if(!next || t < next) next = t; }
    }
  }
  return {prev: prev, next: next};
}
function hhmm(d){
  return d ? ('0'+d.getHours()).slice(-2) + ':' + ('0'+d.getMinutes()).slice(-2) : '—';
}
function dayLabel(d, now){
  if(!d) return '';
  var a = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var b = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  var diff = Math.round((b.getTime() - a.getTime()) / 86400000);
  if(diff === 0) return '今天 ';
  if(diff === 1) return '明天 ';
  return ['周日','周一','周二','周三','周四','周五','周六'][d.getDay()] + ' ';
}

/* ---------- 美股市场情绪：每分钟直连 CNN 检查 ----------
   CNN 的接口带 Access-Control-Allow-Origin: *，浏览器能直接 fetch（实测 19ms，gzip 后 29KB）。
   但这个指数本身是**日频**（美东收盘后更新一次），所以多数时候数字不会变 ——
   每分钟轮询的意义是「它一更新页面就反映」，而不是「数字每分钟在跳」。
   失败一律静默降级：继续显示服务端渲染的跑批快照，不弹错、不影响别的区块。 */
function applyMood(score){
  const m = P.latest && P.latest.mood;
  if(!m || !m.zones || m.zones.length < 5) return false;
  let zone = null;
  for(let i = 0; i < m.zones.length; i++){
    if(m.zones[i][0] <= score && score <= m.zones[i][1]){ zone = m.zones[i]; break; }
  }
  if(!zone) return false;

  const sc = document.getElementById('mood-sc');
  const lb = document.getElementById('mood-lb');
  const pin = document.getElementById('mood-pin');
  if(!sc || !lb || !pin) return false;

  sc.textContent = score.toFixed(1);
  sc.style.color = zone[3];
  lb.textContent = zone[2];
  lb.style.color = zone[3];
  pin.style.left = (Math.max(0, Math.min(100, score)) / 101 * 100).toFixed(2) + '%';
  const pinTxt = pin.querySelector('span');
  if(pinTxt) pinTxt.textContent = Math.round(score);

  const lis = document.querySelectorAll('#mood-zl li');
  for(let j = 0; j < lis.length; j++){
    if(+lis[j].getAttribute('data-lo') === zone[0]) lis[j].classList.add('on');
    else lis[j].classList.remove('on');
  }
  return true;
}

/* CNN 这个口国内经常连不上。原来每分钟无超时地拉一次，请求会一直挂着占住连接，
   手机上表现为「页面一直在转、很卡」。现在：8 秒硬超时 + 连续失败退避
   （1 次→1 分钟，2 次→5 分钟，3 次以上→15 分钟），断了就不折腾。 */
let _moodFail = 0, _moodNext = 0, _moodBusy = false;
function refreshMood(){
  if(document.hidden) return;
  if(_moodBusy) return;                                // 上一发还在路上，别并发
  if(!document.getElementById('mood-sc')) return;      // 本期没这块，不白拉
  if(Date.now() < _moodNext) return;                   // 还在退避窗口里
  const at = document.getElementById('mood-at');
  const ctl = ('AbortController' in window) ? new AbortController() : null;
  const killer = ctl ? setTimeout(function(){ ctl.abort(); }, 8000) : null;
  const done = function(){ _moodBusy = false; if(killer) clearTimeout(killer); };
  _moodBusy = true;
  fetch('https://production.dataviz.cnn.io/index/fearandgreed/graphdata',
        {mode:'cors', cache:'no-store', signal: ctl ? ctl.signal : undefined})
    .then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function(j){
      const fg = (j && j.fear_and_greed) || {};
      if(fg.score == null || !applyMood(+fg.score)) return;
      _moodFail = 0; _moodNext = 0;
      if(at){
        const d = new Date();
        at.textContent = '直连 CNN 刷新 ' + hhmm(d) + ':' + ('0' + d.getSeconds()).slice(-2);
        at.className = 'at';
      }
    })
    .catch(function(){
      // 跨域被拦 / 超时 / CNN 改接口 → 静默，页面上继续用跑批快照
      _moodFail += 1;
      _moodNext = Date.now() + (_moodFail >= 3 ? 900000 : (_moodFail === 2 ? 300000 : 60000));
      if(at){ at.textContent = '直连 CNN 暂不可用，显示跑批快照'; at.className = 'at idle'; }
    })
    .then(done, done);
}

/* ---------- 超短线擒龙：A 股交易时段每分钟直连东财刷新 ----------
   涨停/炸板/跌停池、概念板块、行业成分都是东财公开接口，带 CORS（实测
   Access-Control-Allow-Origin 回显请求 Origin），浏览器能直接 fetch。
   服务端跑批仍保留，作为盘前盘后 + 首屏快照；前端只在 A 股交易时段
   （工作日 09:30-11:30 / 13:00-15:00）每分钟重拉重算，失败一律静默降级到快照。
   逻辑与 src/zhulong.py 完全一致（字段口径、三因子打分），改一边记得同步另一边。 */

function zlInSession(){
  const n = new Date();
  const d = n.getDay();
  if(d === 0 || d === 6) return false;      // 周末
  const m = n.getHours() * 60 + n.getMinutes();
  return (m >= 570 && m <= 690) || (m >= 780 && m <= 900);  // 09:30-11:30 / 13:00-15:00
}
function zlToday(){
  const n = new Date();
  const p = function(x){ return ('0' + x).slice(-2); };
  return n.getFullYear() + p(n.getMonth() + 1) + p(n.getDate());
}
function zlFmtTime(t){
  t = parseInt(t, 10);
  if(isNaN(t)) return '';
  const h = Math.floor(t / 10000), mm = Math.floor(t % 10000 / 100);
  return ('0' + h).slice(-2) + ':' + ('0' + mm).slice(-2);
}
function zlYi(v){
  v = parseFloat(v);
  if(isNaN(v)) return '—';
  if(v >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if(v >= 1e4) return Math.round(v / 1e4) + '万';
  return Math.round(v) + '';
}
function zlClean(r){
  const lbc = parseInt(r.lbc || '0', 10) || 0;
  const zttj = r.zttj || {};
  const ct = parseInt(zttj.ct || '0', 10) || lbc;
  const days = zttj.days ? parseInt(zttj.days, 10) : 0;
  let cycle = '';
  if(days && ct && days !== ct) cycle = days + '天' + ct + '板';
  const zf = (r.zf != null && r.zf !== '') ? Math.round(parseFloat(r.zf) * 100) / 100 : null;
  return {
    code: String(r.c || ''), name: String(r.n || ''),
    price: Math.round(parseFloat(r.p || '0') / 1000 * 100) / 100,
    chg: Math.round(parseFloat(r.zdp || '0') * 100) / 100,
    hs: Math.round(parseFloat(r.hs || '0') * 100) / 100,
    hybk: String(r.hybk || '—'),
    lbc: lbc, ct: ct, zbc: parseInt(r.zbc || '0', 10) || 0,
    fund: zlYi(r.fund), amount: zlYi(r.amount),
    fbt: zlFmtTime(r.fbt), zf: zf,
    label: lbc <= 1 ? '首板' : lbc + '连板', cycle: cycle
  };
}
function zlThemes(pool){
  const by = {};
  pool.forEach(function(r){
    const k = r.hybk;
    if(!by[k]) by[k] = {name: k, count: 0, max_lbc: 0, leader: null};
    by[k].count++;
    if(r.lbc > by[k].max_lbc){ by[k].max_lbc = r.lbc; by[k].leader = r.name; }
  });
  const items = [];
  for(const k in by) items.push(by[k]);
  items.sort(function(a, b){ return (b.count - a.count) || (b.max_lbc - a.max_lbc); });
  return items;
}
function zlDragonReason(d){
  const lbc = d.lbc || 0, hs = d.hs || 0, zbc = d.zbc || 0;
  if(lbc >= 4) return '空间龙头已高位，追高风险大，仅作风向标';
  if(hs < 3) return lbc + '板一字板，封单锁死买不进';
  if(zbc >= 4) return lbc + '板反复炸板' + zbc + '次，分歧极大，谨慎不追';
  if(zbc >= 1) return lbc + '板炸板' + zbc + '次后回封，弱转强可关注';
  return lbc + '板换手板，可等分歧转一致时介入';
}
function zlCatchupReason(chg){
  if(chg < 8) return '同题材龙头已连板，低位补涨，可现价买入';
  if(chg <= 15) return '同题材强势补涨，涨幅已拉开，等回踩不追高';
  return '已近涨停属追高，仅观察不追';
}
/* 梯队 + 可信度：与 src/zhulong.py 的 _tier / _conf 完全一致，改一边同步另一边 */
function zlTier(lbc){
  if(lbc >= 3) return '龙头';
  if(lbc === 2) return '中军';
  return '补涨';
}
function zlConf(tier, lbc, zbc, hs, chg){
  if(tier === '龙头'){
    if(zbc >= 4) return '低';
    if(lbc >= 4 || zbc >= 1 || hs < 3) return '中';
    return '高';
  }
  if(tier === '中军') return (zbc >= 1 ? '低' : '中');
  return (chg >= 8 ? '低' : '中');
}
function zlBuyable(tier, lbc, zbc, hs, chg){
  if(tier === '补涨') return chg < 8;
  return hs >= 3 && zbc === 0 && lbc < 4;
}
function zlThemePicks(themes, dragon, catchup, nTheme){
  nTheme = nTheme || 5;
  function mainboard(code){ const p = String(code || '').slice(0, 2); return p === '60' || p === '00'; }
  dragon = dragon.filter(function(d){ return mainboard(d.code); });
  catchup = catchup.filter(function(c){ return mainboard(c.code); });
  const leadBy = {};
  dragon.forEach(function(d){
    const k = d.hybk || '—';
    const cur = leadBy[k];
    if(!cur || (d.lbc || 0) > (cur.lbc || 0)) leadBy[k] = d;
  });
  const cuBy = {};
  catchup.forEach(function(c){
    if(!cuBy[c.theme]) cuBy[c.theme] = [];
    cuBy[c.theme].push(c);
  });
  const picks = [];
  themes.slice(0, nTheme).forEach(function(t){
    const name = t.name;
    const ld = leadBy[name];
    let leader = null;
    if(ld){
      const lbc = ld.lbc || 0, zbc = ld.zbc || 0, hs = ld.hs || 0, chg = ld.chg || 0;
      const tier = zlTier(lbc);
      leader = {name: ld.name, code: ld.code, label: ld.label, lbc: lbc, chg: chg, hs: hs,
        fund: ld.fund, tier: tier, conf: zlConf(tier, lbc, zbc, hs, chg),
        buyable: zlBuyable(tier, lbc, zbc, hs, chg), reason: zlDragonReason(ld)};
    }
    const cus = (cuBy[name] || []).slice();
    cus.sort(function(a, b){
      const ab = (a.chg < 8) ? 0 : 1, bb = (b.chg < 8) ? 0 : 1;
      return (ab - bb) || (b.chg - a.chg);
    });
    const cu = cus[0] || null;
    let cp = null;
    if(cu){
      const chg = cu.chg || 0, hs = cu.hs || 0;
      cp = {name: cu.name, code: cu.code, chg: chg, hs: hs, tier: '补涨',
        conf: zlConf('补涨', 0, 0, 0, chg), buyable: zlBuyable('补涨', 0, 0, 0, chg),
        reason: zlCatchupReason(chg)};
    }
    picks.push({theme: name, count: t.count, leader: leader, catchup: cp});
  });
  return picks;
}
function zlCatchup(themes, pool){
  const ztCodes = {};
  pool.forEach(function(r){ ztCodes[r.code] = 1; });
  const top3 = themes.slice(0, 3);
  const mapP = _zlIndMap ? Promise.resolve(_zlIndMap) :
    zlFetch('https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=0&np=1&fltt=2&invt=2&fid=f12&fs=m:90+t:2&fields=f12,f14')
      .then(function(j){
        const m = {};
        ((j.data || {}).diff || []).forEach(function(it){ if(it.f14) m[it.f14] = it.f12; });
        _zlIndMap = m;
        return m;
      }).catch(function(){ return {}; });
  return mapP.then(function(indMap){
    const tasks = top3.map(function(th){
      const bk = indMap[th.name];
      if(!bk) return Promise.resolve([]);
      return zlFetch('https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=40&po=1&np=1&fltt=2&invt=2&fid=f3&fs=b:' + bk + '&fields=f2,f3,f8,f12,f14')
        .then(function(j){
          const out = [];
          (((j.data || {}).diff) || []).forEach(function(it){
            const code = it.f12, chg = Math.round(parseFloat(it.f3 || '0') * 100) / 100;
            if(out.length >= 4) return;
            if(ztCodes[code]) return;
            if(chg <= 0) return;
            out.push({theme: th.name, code: code, name: it.f14,
              chg: chg, hs: Math.round(parseFloat(it.f8 || '0') * 100) / 100});
          });
          return out;
        }).catch(function(){ return []; });
    });
    return Promise.all(tasks).then(function(arr){
      const out = [];
      arr.forEach(function(a){ for(let i = 0; i < a.length; i++) out.push(a[i]); });
      return out;
    });
  });
}
function zlRenderDyn(zl){
  const mkt = zl.market || {};
  const st = function(lbl, val, cls){
    return '<div class="st"><span class="lbl">' + lbl + '</span><b class="' + (cls || '') + '">' + esc(val) + '</b></div>';
  };
  const stats = '<div class="zl-stats">'
    + st('涨停', (mkt.zt != null ? mkt.zt : '—'), 'up')
    + st('炸板', (mkt.zb != null ? mkt.zb : '—'), '')
    + st('跌停', (mkt.dt != null ? mkt.dt : '—'), 'dn')
    + st('最高板', (mkt.max_lbc ? mkt.max_lbc + '连板' : '—'), '')
    + '</div>';
  const confCls = function(txt){ return txt === '高' ? 'cf cf-hi' : (txt === '低' ? 'cf cf-lo' : 'cf cf-mid'); };
  const pickRow = function(label, badgeCls, p){
    if(!p) return '<div class="zp-row empty"><span class="zp-role ' + badgeCls + '">' + label + '</span>'
      + '<span class="zp-none">本期无</span></div>';
    const buyCls = p.buyable ? ' buyable' : '';
    const buyTag = p.buyable ? '<span class="zp-buy-tag">买</span>' : '';
    const cf = p.conf ? '<span class="' + confCls(p.conf) + '">可信·' + esc(p.conf) + '</span>' : '';
    return '<div class="zp-row' + buyCls + '">'
      + '<span class="zp-role ' + badgeCls + '">' + label + '</span>'
      + '<div class="zp-info">'
      +   '<div class="zp-nm">' + esc(p.name) + '<span class="zp-cd">' + esc(p.code) + '</span></div>'
      +   '<div class="zp-meta">' + (p.label ? esc(p.label) + ' · ' : '')
      +     '涨幅 <span class="up">' + ((p.chg > 0 ? '+' : '') + p.chg.toFixed(2)) + '%</span>'
      +     (p.lbc ? ' · 封单 ' + esc(p.fund || '—') : '')
      +     ' · 换手 ' + (p.hs || 0).toFixed(1) + '%</div>'
      +   '<div class="zp-rs">' + esc(p.reason) + '</div>'
      + '</div>' + cf + buyTag + '</div>';
  };
  let pickCards = '';
  (zl.picks || []).forEach(function(pk){
    pickCards += '<div class="zp-card">'
      + '<div class="zp-hd">' + esc(pk.theme) + '<span class="zp-cnt">' + pk.count + '家涨停</span></div>'
      + pickRow('领涨龙头', 'lead', pk.leader)
      + pickRow('补涨龙头', 'cu', pk.catchup)
      + '</div>';
  });
  let picksHtml = '';
  if(pickCards){
    picksHtml = '<div class="zl-picks"><div class="hd">按题材分组 · 领涨/补涨龙头 '
      + '<span class="hint">每个热点题材只留最强的两只 · 可买标红 + 红色「买」字</span></div>'
      + '<div class="zp-grid">' + pickCards + '</div></div>';
  }
  let chips = '';
  (zl.concepts || []).slice(0, 8).forEach(function(c){
    chips += '<span class="chip">' + esc(c.name) + ' <b>' + ((c.chg > 0 ? '+' : '') + c.chg.toFixed(2)) + '%</b></span>';
  });
  const tags = '<div class="zl-tags"><span class="tagk">题材温度</span>' + chips + '</div>';
  let themeRows = '';
  (zl.themes || []).slice(0, 8).forEach(function(t){
    themeRows += '<tr><td class="nm">' + esc(t.name) + '</td>'
      + '<td class="r up"><b>' + t.count + '</b></td>'
      + '<td class="r">' + t.max_lbc + '板</td>'
      + '<td class="dim">' + esc(t.leader || '—') + '</td></tr>';
  });
  let themesHtml = '';
  if(themeRows){
    themesHtml = '<div class="zl-ct">热点题材榜 <span class="hint">按涨停家数计 · 涨停潮所在 = 题材所在</span></div>'
      + '<div class="zl-scroll"><table class="zl-tbl"><thead><tr><th>题材(行业)</th><th class="r">涨停家数</th>'
      + '<th class="r">最高板</th><th>龙头</th></tr></thead><tbody>' + themeRows + '</tbody></table></div>';
  }
  const badge = function(row){
    const lbc = row.lbc || 0;
    const cls = lbc >= 3 ? 'zl-badge' : 'zl-badge gold';
    return '<span class="' + cls + '">' + esc(row.label || '首板') + '</span>';
  };
  let dragonRows = '';
  (zl.dragon || []).slice(0, 15).forEach(function(d){
    const cyc = d.cycle ? ' <span class="zl-badge cycle">' + esc(d.cycle) + '</span>' : '';
    dragonRows += '<tr><td class="nm">' + esc(d.name) + '<span class="cd"> ' + esc(d.code) + '</span></td>'
      + '<td>' + badge(d) + cyc + '</td>'
      + '<td class="dim">' + esc(d.hybk || '—') + '</td>'
      + '<td class="r dim">' + esc(d.fbt || '—') + '</td>'
      + '<td class="r">' + esc(d.fund || '—') + '</td>'
      + '<td class="r dim">' + (d.hs || 0).toFixed(1) + '%</td></tr>';
  });
  let dragonHtml = '';
  if(dragonRows){
    dragonHtml = '<div class="zl-ct">龙头梯队 <span class="hint">连板 ≥ 2 · 最高板 = 空间龙头</span></div>'
      + '<div class="zl-scroll"><table class="zl-tbl"><thead><tr><th>名称</th><th>连板</th><th>行业</th>'
      + '<th class="r">封板</th><th class="r">封单</th><th class="r">换手</th></tr></thead><tbody>' + dragonRows + '</tbody></table></div>';
  }
  let zbRows = '';
  (zl.zhaban || []).slice(0, 10).forEach(function(z){
    const chg = z.chg || 0;
    const chgCls = chg > 0 ? 'up' : (chg < 0 ? 'dn' : 'dim');
    const chgTxt = (chg > 0 ? '+' : '') + chg.toFixed(2) + '%';
    const cyc = z.cycle ? ' <span class="zl-badge cycle">' + esc(z.cycle) + '</span>' : '';
    zbRows += '<tr><td class="nm">' + esc(z.name) + '<span class="cd"> ' + esc(z.code) + '</span></td>'
      + '<td><span class="zl-badge zb">炸板' + (z.zbc || 0) + '次</span>' + cyc + '</td>'
      + '<td class="r dim">' + (z.zf != null ? z.zf + '%' : '—') + '</td>'
      + '<td class="r dim">' + (z.hs || 0).toFixed(1) + '%</td>'
      + '<td class="r ' + chgCls + '">' + (z.price || 0).toFixed(2) + ' (' + chgTxt + ')</td></tr>';
  });
  let zbHtml = '';
  if(zbRows){
    zbHtml = '<div class="zl-ct">异动监控 <span class="hint">炸板 = 涨停后打开 · 龙头分歧信号</span></div>'
      + '<div class="zl-scroll"><table class="zl-tbl"><thead><tr><th>名称</th><th>状态</th>'
      + '<th class="r">振幅</th><th class="r">换手</th><th class="r">现价</th></tr></thead><tbody>' + zbRows + '</tbody></table></div>';
  }else{
    zbHtml = '<div class="zl-ct">异动监控 <span class="hint">今日无炸板，封板情绪强</span></div>'
      + '<div class="zl-zb-note">涨停板池中炸板次数均为 0。</div>';
  }
  let cuRows = '';
  (zl.catchup || []).slice(0, 12).forEach(function(c){
    cuRows += '<tr><td class="nm">' + esc(c.name) + '<span class="cd"> ' + esc(c.code) + '</span></td>'
      + '<td class="dim">' + esc(c.theme) + '</td>'
      + '<td class="r up">' + ((c.chg > 0 ? '+' : '') + c.chg.toFixed(2)) + '%</td>'
      + '<td class="r dim">' + (c.hs || 0).toFixed(1) + '%</td></tr>';
  });
  let cuHtml = '';
  if(cuRows){
    cuHtml = '<div class="zl-ct">补涨候选 <span class="hint">热点题材中 · 今日上涨但未封板 · 龙头高位后的接力/补涨观察</span></div>'
      + '<div class="zl-scroll"><table class="zl-tbl"><thead><tr><th>名称</th><th>题材</th>'
      + '<th class="r">涨幅</th><th class="r">换手</th></tr></thead><tbody>' + cuRows + '</tbody></table></div>';
  }else{
    cuHtml = '<div class="zl-ct">补涨候选 <span class="hint">本期未取到（行业成分接口不可用）</span></div>';
  }
  return stats + picksHtml + tags + themesHtml + '<div class="zl-grid">' + dragonHtml + zbHtml + '</div>' + cuHtml;
}
function zlFetch(url){
  const ctl = ('AbortController' in window) ? new AbortController() : null;
  const killer = ctl ? setTimeout(function(){ ctl.abort(); }, 8000) : null;
  const p = fetch(url, {mode: 'cors', cache: 'no-store', signal: ctl ? ctl.signal : undefined});
  p.then(function(){ if(killer) clearTimeout(killer); },
         function(){ if(killer) clearTimeout(killer); });
  return p.then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
}
let _zlBusy = false, _zlFail = 0, _zlNext = 0, _zlIndMap = null, _zlLastHtml = '';
function zlSetAt(txt, cls){
  const at = document.getElementById('zl-at');
  if(at){ at.textContent = txt || ''; at.className = 'zl-at' + (cls ? ' ' + cls : ''); }
}
function zlDone(ok, date){
  _zlBusy = false;
  if(ok){
    _zlFail = 0; _zlNext = 0;
    const n = new Date();
    const dd = date ? (date.slice(0, 4) + '-' + date.slice(4, 6) + '-' + date.slice(6, 8)) : '';
    zlSetAt('直连东财刷新 ' + hhmm(n) + ':' + ('0' + n.getSeconds()).slice(-2) + (dd ? ' · ' + dd : ''));
  }else{
    _zlFail += 1;
    _zlNext = Date.now() + (_zlFail >= 3 ? 900000 : (_zlFail === 2 ? 300000 : 60000));
    zlSetAt('直连东财暂不可用，显示跑批快照', 'warn');
  }
}
function refreshZhulong(){
  if(document.hidden) return;
  if(_zlBusy) return;
  const dyn = document.getElementById('zl-dyn');
  if(!dyn) return;                                  // 本期没这块，不白拉
  if(!zlInSession()){ if(!_zlBusy) zlSetAt('', ''); return; }  // 非交易时段：清掉实时标注，保留快照
  if(Date.now() < _zlNext) return;                  // 失败退避窗口内
  _zlBusy = true;
  const date = zlToday();
  const U = 'https://push2ex.eastmoney.com/getTopic';
  const ut = '7eea3edcaed734bea9cbfc24409ed989', dpt = 'wz.ztzt';
  const q = function(kind, sort){
    return U + kind + '?ut=' + ut + '&dpt=' + dpt + '&Pageindex=0&pagesize=400&sort=' + sort + '&date=' + date;
  };
  const pZt = zlFetch(q('ZTPool', 'fbt:asc')).then(function(j){ return ((j.data || {}).pool) || []; });
  const pZb = zlFetch(q('ZBPool', 'fbt:asc')).then(function(j){ return ((j.data || {}).pool) || []; });
  const pDt = zlFetch(q('DTPool', 'fund:asc')).then(function(j){ return ((j.data || {}).pool) || []; });
  const pCon = zlFetch('https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=8&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:3&fields=f2,f3,f12,f14')
    .then(function(j){ return ((j.data || {}).diff) || []; });
  Promise.all([pZt, pZb, pDt, pCon]).then(function(arr){
    const pool = arr[0].map(zlClean);
    const zb = arr[1].map(zlClean);
    const dtPool = arr[2].map(zlClean);
    const concepts = arr[3].map(function(it){
      return {name: it.f14, code: it.f12, chg: Math.round(parseFloat(it.f3 || '0') * 100) / 100};
    });
    if(!pool.length){ zlDone(false); return; }       // 早盘瞬间今日池还没生成，保持快照
    const themes = zlThemes(pool);
    const dragon = pool.filter(function(r){ return r.lbc >= 2; })
      .sort(function(a, b){
        return (b.lbc - a.lbc) || (b.ct - a.ct) || (a.fbt < b.fbt ? -1 : (a.fbt > b.fbt ? 1 : 0));
      });
    zlCatchup(themes, pool).then(function(catchup){
      const zl = {
        market: {
          zt: pool.length, zb: zb.length, dt: dtPool.length,
          max_lbc: pool.reduce(function(a, r){ return Math.max(a, r.lbc); }, 0)
        },
        concepts: concepts, themes: themes, dragon: dragon,
        zhaban: zb, catchup: catchup, picks: zlThemePicks(themes, dragon, catchup)
      };
      const html = zlRenderDyn(zl);
      if(html !== _zlLastHtml){ dyn.innerHTML = html; _zlLastHtml = html; }
      const set = function(id, t){ const e = document.getElementById(id); if(e) e.textContent = t; };
      set('zl-date', date.slice(0, 4) + '-' + date.slice(4, 6) + '-' + date.slice(6, 8));
      set('zl-zt', pool.length); set('zl-zb', zb.length);
      set('zl-maxlbc', zl.market.max_lbc + ' 连板');
      zlDone(true, date);
    }).catch(function(){ zlDone(false); });
  }).catch(function(){ zlDone(false); });
}

/* 非交易日说明：周六周日跑批照跑（抓隔夜美股 / MSCI），但 A 股不开盘，
   trade_date 必然停在最近一个交易日。不写清楚，用户会以为「页面没更新」——
   2026-10-31（周六）就为此被问了一次。 */
function restTag(td){
  if(!td) return '';
  const n = new Date();
  const p = function(x){ return ('0'+x).slice(-2); };
  const today = n.getFullYear()+'-'+p(n.getMonth()+1)+'-'+p(n.getDate());
  if(td >= today) return '';
  const w = n.getDay();
  if(w === 0 || w === 6) return '<span class="idle nw">（周末休市）</span>';
  return '<span class="idle nw">（非今日）</span>';
}

function render(){
  const L = P.latest;
  // 数据新鲜度：用 epoch 秒算（没有就退回解析本地时间字符串），
  // 页面上直接告诉你「这次数据是几小时前的」，比只写一个生成时刻有用
  let ageH = null;
  if(L.generated_at_ts){ ageH = (Date.now()/1000 - L.generated_at_ts)/3600; }
  else if(L.generated_at){
    const t = Date.parse(String(L.generated_at).replace(/-/g,'/'));
    if(!isNaN(t)) ageH = (Date.now()-t)/3600000;
  }
  let genMs = null;
  if(L.generated_at_ts) genMs = L.generated_at_ts * 1000;
  else if(L.generated_at){
    const t2 = Date.parse(String(L.generated_at).replace(/-/g,'/'));
    if(!isNaN(t2)) genMs = t2;
  }

  const span = schedSpan(P.schedule);
  const now = new Date();
  let stateTxt = '', stateCls = 'idle';
  if(ageH != null && ageH >= 0){
    // 计划点刚过 15 分钟内算「正在跑」：一次跑批实测 2~3 分钟，加上 GitHub 排队更久，
    // 这时候标红说「没更新」是冤枉它。
    const lateMin = span && span.prev ? (now.getTime() - span.prev.getTime()) / 60000 : null;
    const missed = !!(span && span.prev && genMs != null && genMs < span.prev.getTime() - 60000);
    if(lateMin != null && lateMin >= 0 && lateMin < 15){
      stateTxt = '计划 ' + hhmm(span.prev) + ' 批次更新中';
    }else if(missed){
      stateTxt = '上次 ' + hhmm(span.prev) + ' 未触发'; stateCls = 'warn';
    }else if(ageH < 1.5){
      stateTxt = '刚更新'; stateCls = 'ok';
    }else{
      stateTxt = ageH.toFixed(0) + ' 小时前';
    }
  }
  const nTxt = span && span.next
    ? '下次 ' + dayLabel(span.next, now) + hhmm(span.next)
    : '';
  const perDay = (P.schedule && P.schedule.tods) ? P.schedule.tods.length : 0;

  document.getElementById('meta').innerHTML =
    '<span class="ln"><span class="dot"></span><span class="k">分数快照</span>' +
      '<b>' + (L.trade_date || '') + '</b>' + restTag(L.trade_date) + ' · ' +
      (L.generated_at || '').slice(11, 16) + ' 生成' +
      (stateTxt ? ' · <span class="' + stateCls + ' nw">' + stateTxt + '</span>' : '') +
      (nTxt ? ' · <span class="idle nw">' + nTxt + '</span>' : '') + '</span>' +
    '<span class="ln rt"><span class="k">实时价格</span>每 60 秒自动刷新' +
      (perDay ? ' · 分数每交易日 ' + perDay + ' 次' : '') + '</span>' +
    '<span class="ln"><span class="k">基准</span><b>' +
      L.base_amount.toLocaleString('zh-CN') + ' 元/月</b> · 历史 <b>' +
      P.history.length + '</b> 期</span>';

  // 结论条：全部标的里分数最高的（含参考指数则标注）
  const ex_ = L.assets.filter(a=>!a.advisory_only);
  const sorted = ex_.slice().sort((a,b)=>b.score-a.score);
  const top = sorted[0], low = sorted[sorted.length-1];
  const upN = ex_.filter(a=>a.multiplier>1.02).length;
  // hero 三个数字全是分数派生的快照，不是实时值 —— 必须标出来，
  // 否则上面正好有一条每分钟刷新的行情条，很容易被当成"整页都在实时跑"。
  document.getElementById('hero').innerHTML =
    '<div><div class="k">本期最该加仓<i class="fqmini">快照</i></div><div class="v pick">'+esc(top.name)+
      '</div><div class="hint">'+top.score.toFixed(1)+' 分 · '+top.multiplier.toFixed(1)+
      '× · '+(top.suggest_amount?top.suggest_amount.toLocaleString('zh-CN')+' 元':'—')+'</div></div>'+
    '<div><div class="k">相对最贵<i class="fqmini">快照</i></div><div class="v">'+esc(low.name)+
      '</div><div class="hint">'+low.score.toFixed(1)+' 分 · '+low.multiplier.toFixed(1)+'×</div></div>'+
    '<div><div class="k">上调档位<i class="fqmini">快照</i></div><div class="v">'+upN+' / '+ex_.length+
      '</div><div class="hint">超过 1.0 倍的标的数</div></div>';

  const m = L.macro||{};
  const cells = [
    ['美债10Y 实际利率', m.ust_10y_real, '%'],
    ['美债10Y 名义利率', m.ust_10y_nominal, '%'],
    ['美元指数 DXY', m.dxy, ''],
    ['USDCNH', m.usdcnh, ''],
    ['伦敦金现', m.gold_spot, '']
  ];
  document.getElementById('macro').innerHTML = cells.map(function(c){
    const k=c[0], v=c[1], u=c[2];
    return '<div><div class="k">'+k+'<i class="fqmini">日频</i></div><div class="v num">'+
    (v==null?'—':v.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:4}))+
    (u?'<small>'+u+'</small>':'')+'</div></div>'; }).join('');

  const g = document.getElementById('grid');
  g.innerHTML = L.assets.map(function(a){
    const ex = a.execution||{};
    const dir = a.advisory_only ? 'ref' : '';
    const mult = a.multiplier.toFixed(1);
    const bp = (a.band_pos==null?50:a.band_pos);
    const dims = (a.dimensions||[]).map(function(d){
      const cn = {valuation:'估值',trend:'趋势',sentiment:'情绪',macro:'宏观'}[d.key]||d.key;
      return '<div class="dim"><div class="r"><span>'+cn+' <span style="color:var(--dim3)">'+
        d.weight+'%</span></span><b class="num">'+d.score.toFixed(1)+'</b></div>'+
        '<div class="t"><div class="f" style="width:'+Math.max(2,Math.min(100,d.score))+
        '%;background:'+dimColor(d.score)+'"></div></div></div>';
    }).join('');
    const fund = a.advisory_only
      ? '<div class="fund"><span>仅作市场温度参考</span><span class="st">不产生动作</span></div>'
      : (ex.fund_code
        ? '<div class="fund"><span>落地 <span class="code">'+esc(ex.fund_code)+'</span> '+
          (ex.nav!=null?'净值 '+ex.nav.toFixed(4):'')+'</span>'+
          '<span class="st '+stCls(ex.subscribe_status)+'">'+esc(ex.subscribe_status||'—')+'</span></div>'
        : '<div class="fund"><span>该口径无对应场外基金</span><span class="st">仅指数评分</span></div>');
    return '<div class="card '+dir+'">'+
      '<div class="top"><div><div class="nm">'+esc(a.name)+'</div>'+
      '<div class="px num">收盘 '+fmtPx(a.price)+' · '+(a.price_date||'')+'</div></div>'+
      '<div class="tag">'+(a.advisory_only?'参考':'可执行')+'</div></div>'+
      '<div class="mid"><div class="score num">'+a.score.toFixed(1)+'<small>分</small></div>'+
      '<div class="mult '+multCls(a.multiplier)+' num">'+(a.advisory_only?'—':mult+'×')+'</div>'+
      '<div class="lbl">'+(a.advisory_only?'不执行':esc(a.label))+'<br>档内 '+bp.toFixed(0)+'%</div></div>'+
      '<div class="band"><div class="track"><div class="fill" style="width:'+Math.max(2,bp)+'%"></div></div>'+
      '<div class="cap"><span>本档下沿</span><span>越靠右越接近上调</span></div></div>'+
      '<div class="dims">'+dims+'</div>'+sparkBlock(a)+fund+'</div>';
  }).join('');

  renderChart();
}

let CHART_WIN = (function(){                     // 0 = 全部；可用 ?w=22 直接打开某个窗口
  const m = new URLSearchParams(window.location.search).get('w');
  return m ? (parseInt(m, 10) || 0) : 0;
})();
function renderChart(){
  const S = P.series||{};
  const ids = (S.ids||[]).filter(function(id){ return id!=='IXIC'; });
  const box = document.getElementById('chart');
  const bar = document.getElementById('chartbar');
  const full = P.history.length;
  if(full < 2){
    box.innerHTML = '<div style="padding:28px;text-align:center;color:var(--dim3);font-size:12px;letter-spacing:.05em">'+
      '历史曲线需要至少 2 个交易日，当前第 <b style="color:var(--dim)">'+full+
      '</b> 天。每天跑批自动累积，250 期后形成完整一年曲线。</div>';
    if(bar) bar.innerHTML = '';
    return;
  }
  const n = (CHART_WIN && CHART_WIN < full) ? CHART_WIN : full;   // 窗口内期数
  const off = full - n;                                          // 窗口起点在历史数组里的下标
  // 手机上按窄视口重设画布：viewBox 宽 1100 缩到 375px 会把线和字一起压成 1/3，
  // 这也是「手机上图太浅」的真正原因，不只是配色淡。
  const narrow = (window.innerWidth || 1200) < 640;
  const W = narrow ? 430 : 1100, H = narrow ? 350 : 330;
  const PL = narrow ? 26 : 40, PT = narrow ? 16 : 22, PB = narrow ? 26 : 30;
  // ★ 颜色必须按**标的 id** 查表，不能按下标轮。
  //   按下标轮时，同一只标的在「近一月涨跌图」（Python 侧 MONTH_COLORS）和这张分数图里
  //   颜色不一样 —— 2026-10-31 自查发现：近一月图里黄金是棕、纳指100 是蓝，
  //   分数图里黄金却成了黑、纳指100 成了棕。读者换一张图就得重新认一遍线，比没颜色更糟。
  //   下面这张表与 Python 的 MONTH_COLORS 必须逐字一致（selfcheck 有断言比对）。
  const COLORS = {
    IXIC:'#111827', NDX:'#2f6fb0', GOLD:'#a8752a',
    MSCI_HEALTH:'#2f7d5e', CSI_DIVIDEND:'#b4512f'
  };
  const COLORS_FB = ['#5b4b8a','#7a7f8c','#3f7f9e','#8a6b25','#9c4f4f'];
  const colorOf = function(id, i){ return COLORS[id] || COLORS_FB[i % COLORS_FB.length]; };
  // 曲线右端要标「指数名 + 当前分数」，右侧留白不能再写死 16（塞不下一个字）。
  // 按最长的那个名字算，上限 0.34×画布宽；窄画布一行放不下就改两行（名称在上、分数在下）。
  const stack = W < 600;
  const nfs = 10, pfs = 11;
  const pcap = tw('-88.8', pfs);
  const room = Math.max(56, W * 0.34);
  const namecap = room - 12 - (stack ? 0 : (7 + 4 + pcap));
  const labName = ids.map(function(id){ return ellip(cname((S.names||{})[id]||id), nfs, namecap); });
  let need = 0;
  labName.forEach(function(nm){
    need = Math.max(need, stack ? Math.max(tw(nm, nfs), pcap) : (7 + tw(nm, nfs) + 4 + pcap));
  });
  // +12 = 标签相对线端点的左偏 7 加上安全余量，少了这几个单位字就顶出 viewBox
  const PR = Math.min(Math.max(56, need + 12), room);
  // 每条约曲线只取「窗口内的尾部」：某天某标的缺数据时不会把整条线整体左移
  const tail = function(id){
    const a = S.data[id]||[];
    return a.length>=full ? a.slice(off) : a.slice(Math.max(0, a.length-n));
  };
  const all = [];
  ids.forEach(function(id){ tail(id).forEach(function(p){ if(p.s!=null) all.push(p.s); }); });
  if(!all.length){
    box.innerHTML = '<div style="padding:28px;text-align:center;color:var(--dim3);font-size:12px">暂无分数序列</div>';
    return;
  }
  const mn = Math.max(0, Math.min.apply(null, all)-5);
  const mx = Math.min(100, Math.max.apply(null, all)+5);
  const x = function(i){ return PL + (n<=1?0:(W-PL-PR)*i/(n-1)); };
  const y = function(v){ return PT + (H-PT-PB)*(1-(v-mn)/Math.max(1e-9,mx-mn)); };

  let svg = '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet">';
  svg += '<defs>';
  ids.forEach(function(id,ci){
    svg += '<linearGradient id="g'+ci+'" x1="0" y1="0" x2="1" y2="0">'+
      '<stop offset="0%" stop-color="'+colorOf(id, ci)+'" stop-opacity=".7"/>'+
      '<stop offset="55%" stop-color="'+colorOf(id, ci)+'" stop-opacity=".96"/>'+
      '<stop offset="100%" stop-color="'+colorOf(id, ci)+'" stop-opacity="1"/></linearGradient>';
  });
  svg += '</defs>';
  for(let k=0;k<=4;k++){
    const v = mn + (mx-mn)*k/4, yy = y(v);
    svg += '<line x1="'+PL+'" y1="'+yy+'" x2="'+(W-PR)+'" y2="'+yy+
      '" stroke="rgba(20,22,27,.09)" stroke-width="1"/>';
    svg += '<text x="'+(PL-9)+'" y="'+(yy+3.5)+'" fill="#7a7d87" font-size="10" text-anchor="end">'+
      v.toFixed(0)+'</text>';
  }
  if(50>mn && 50<mx){
    svg += '<line x1="'+PL+'" y1="'+y(50)+'" x2="'+(W-PR)+'" y2="'+y(50)+
      '" stroke="rgba(140,105,40,.7)" stroke-width="1.2" stroke-dasharray="5 5"/>';
    // 标签放左端：原来放右端会被收口的四条线压住，手机上完全看不见。
    // 加白色描边（paint-order）让它在曲线上也能读出来
    svg += '<text x="'+(PL+8)+'" y="'+(y(50)-8)+'" fill="#7d5f20" font-size="11.5" '+
      'stroke="#ffffff" stroke-width="3" stroke-linejoin="round" paint-order="stroke fill" '+
      'text-anchor="start" letter-spacing=".6">1.0× 基准 · 50 分</text>';
  }
  ids.forEach(function(id,ci){
    const pts = tail(id);
    if(!pts.length) return;
    const w0 = n - pts.length;   // 不足 n 点时右对齐，末点始终落在「今天」
    const d = pts.map(function(p,i){
      return (i?'L':'M')+x(w0+i).toFixed(1)+' '+y(p.s).toFixed(1); }).join(' ');
    svg += '<path d="'+d+'" fill="none" stroke="url(#g'+ci+')" stroke-width="3" '+
      'stroke-linejoin="round" stroke-linecap="round"/>';
    const last = pts[pts.length-1];
    svg += '<circle cx="'+x(n-1).toFixed(1)+'" cy="'+y(last.s).toFixed(1)+
      '" r="2.8" fill="'+colorOf(id, ci)+'"/>';
  });
  // 末值标签：指数名 + 当前分数，贴在各自曲线右端。
  // 四条线经常收在 35–52 这十几分里（本期 45.8 / 44.6 只差 1.2 分），末端几乎重合，
  // 所以按 y 排序后逐个压开最小间距；被压开的画一小段引线连回真实端点，
  // 否则标签看着像标到了旁边那条线上 —— 这比不标更糟。
  const labs = [];
  ids.forEach(function(id,ci){
    const pts = tail(id); if(!pts.length) return;
    const last = pts[pts.length-1]; if(last.s==null) return;
    labs.push({y0: y(last.s), y: y(last.s), v: last.s,
               c: colorOf(id, ci), nm: labName[ci]});
  });
  labs.sort(function(a,b){ return a.y0 - b.y0; });
  const bh = stack ? (nfs*1.16 + pfs*1.16) : pfs*1.25;   // 单个标签块的高度
  // 两行模式下块间距放大到 1.5 倍块高：名字和自己的分数贴紧、跟邻居拉开
  const lgap = bh * (stack ? 1.5 : 1.32);
  let pre = null;
  labs.forEach(function(L){
    if(pre != null && L.y - pre < lgap) L.y = pre + lgap;
    pre = L.y;
  });
  if(labs.length){
    const over = (labs[labs.length-1].y + bh/2) - (H - PB + 6);
    if(over > 0) labs.forEach(function(L){ L.y -= over; });        // 推到底边外整组上移
    const up = (labs[0].y - bh/2) - 2;
    if(up < 0) labs.forEach(function(L){ L.y -= up; });            // 顶到画布外再压回来
  }
  const xEnd = x(n-1);
  labs.forEach(function(L){
    if(Math.abs(L.y - L.y0) > 0.6){
      svg += '<path d="M'+(xEnd+2).toFixed(1)+' '+L.y0.toFixed(1)+'L'+(xEnd+6).toFixed(1)+' '+
        L.y.toFixed(1)+'" fill="none" stroke="'+L.c+'" stroke-width="1" stroke-opacity=".45"/>';
    }
    if(stack){
      svg += '<text x="'+(xEnd+7).toFixed(1)+'" y="'+(L.y-bh/2+nfs*0.95).toFixed(1)+'" '+
        'fill="'+L.c+'" fill-opacity=".78" font-size="'+nfs+'" paint-order="stroke fill" '+
        'stroke="#fff" stroke-width="2.6" stroke-linejoin="round">'+esc(L.nm)+'</text>';
      svg += '<text x="'+(xEnd+7).toFixed(1)+'" y="'+(L.y+bh/2-pfs*0.22).toFixed(1)+'" '+
        'fill="'+L.c+'" font-size="'+pfs+'" font-weight="600" paint-order="stroke fill" '+
        'stroke="#fff" stroke-width="3" stroke-linejoin="round">'+L.v.toFixed(1)+'</text>';
    }else{
      // 名称与分数放同一个 <text> 的两个 <tspan>：位置交给排版引擎算，
      // 自己估字宽去摆第二个 <text> 一旦估错两个就叠住了（dx 而不是空格，SVG 会吃首尾空白）
      svg += '<text x="'+(xEnd+7).toFixed(1)+'" y="'+(L.y+pfs*0.35).toFixed(1)+'" '+
        'paint-order="stroke fill" stroke="#fff" stroke-width="3" stroke-linejoin="round">'+
        '<tspan fill="'+L.c+'" fill-opacity=".78" font-size="'+nfs+'">'+esc(L.nm)+'</tspan>'+
        '<tspan dx="4" fill="'+L.c+'" font-size="'+pfs+'" font-weight="600">'+
        L.v.toFixed(1)+'</tspan></text>';
    }
  });
  const hist = P.history;
  [0, Math.floor(n/2), n-1].forEach(function(i){
    const dd = (hist[off+i]||{}).trade_date||'';
    svg += '<text x="'+x(i).toFixed(1)+'" y="'+(H-8)+'" fill="#7a7d87" font-size="10" '+
      'letter-spacing=".5" text-anchor="'+(i===0?'start':(i===n-1?'end':'middle'))+'">'+dd+'</text>';
  });
  svg += '</svg>';

  let leg = '<div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:14px;font-size:10.5px;'+
    'color:var(--dim2);letter-spacing:.06em">';
  ids.forEach(function(id,ci){
    const pts = S.data[id]||[]; const lv = pts.length ? pts[pts.length-1].s : null;
    // 图例仍然保留数字：它同时是配色对照表，滚到底部能一次看全四个分数
    leg += '<span style="display:inline-flex;align-items:center;gap:7px">'+
      '<i style="width:12px;height:2px;border-radius:2px;background:'+colorOf(id, ci)+
      ';display:inline-block"></i>'+esc((S.names||{})[id]||id)+
      '<b style="color:var(--txt);font-weight:600;font-variant-numeric:tabular-nums">'+
      (lv==null?'—':lv.toFixed(1))+'</b></span>';
  });
  leg += '</div>';

  // 工具条：手动切窗口（默认全部）+ 每条线「较上一期」的分数变化
  if(bar){
    let bh = '<div class="btns">';
    [[22,'近 1 月'],[66,'近 3 月'],[0,'全部 '+full+' 期']].forEach(function(w){
      if(w[0] && w[0] >= full) return;
      const on = w[0] ? (CHART_WIN===w[0]) : (!CHART_WIN || CHART_WIN>=full);
      bh += '<button type="button" data-w="'+w[0]+'"'+(on?' class="on"':'')+'>'+w[1]+'</button>';
    });
    bh += '</div><div class="delta"><span class="lb">较上一期</span>';
    ids.forEach(function(id,ci){
      const a = S.data[id]||[]; const p1 = a[a.length-2], p2 = a[a.length-1];
      const dv = (p1&&p2&&p1.s!=null&&p2.s!=null) ? (p2.s-p1.s) : null;
      bh += '<span class="dd"><i style="background:'+colorOf(id, ci)+'"></i>'+
        esc((S.names||{})[id]||id)+'<b>'+(dv==null?'—':(dv>0?'+':'')+dv.toFixed(1))+'</b></span>';
    });
    bh += '</div>';
    bar.innerHTML = bh;
    Array.prototype.forEach.call(bar.querySelectorAll('button'), function(btn){
      btn.onclick = function(){
        CHART_WIN = parseInt(btn.getAttribute('data-w'), 10) || 0;
        renderChart();
      };
    });
  }

  box.innerHTML = svg + leg;
}

/* ---------- 实时行情条 ----------
   浏览器直连腾讯行情（script 跨域，不需要 CORS）。取不到就整块隐藏，
   绝不因为外部接口挂了把页面搞白 —— 分数和倍数一律来自服务端快照。 */
const LIVE = [
  {c:'usIXIC',  nm:'纳斯达克综合'},
  {c:'usNDX',   nm:'纳斯达克100'},
  {c:'hf_GC',   nm:'黄金 COMEX'},
  {c:'sh000922',nm:'中证红利'},
  {c:'sh000300',nm:'沪深300'},
  {c:'sz399001',nm:'深证成指'},
  {c:'sz399006',nm:'创业板指'},
  {c:'sh000688',nm:'科创50'},
  {c:'sz399673',nm:'创业板50'}
];
function qcls(v){ return v>0.0001?'up':(v<-0.0001?'dn':'mid'); }
function renderLive(){
  const box=document.getElementById('live'); if(!box) return;
  let cells=[], stamp='';
  LIVE.forEach(function(it){
    const raw=window['v_'+it.c]; if(!raw) return;
    let px=null, pct=null, t='';
    if(it.c.indexOf('hf_')===0){
      const q=String(raw).split(',');
      px=parseFloat(q[0]); pct=parseFloat(q[1]); t=(q[12]||'')+' '+(q[6]||'');
    }else{
      const p=String(raw).split('~');
      px=parseFloat(p[3]);
      // 从后往前找时间戳：A 股是 14 位紧凑时间(20261105161449)，美股带横线(2026-11-05 10:30:40)。
      // ★ 14 位数字必须限定 20 开头(年份 20xx)：
      //   美股行情的成交额字段(如 77819090203785 / 16555717122633)也是 14 位数字、
      //   但以 7/1 开头，排在真时间戳后面 —— 之前用 [0-9]{14} 从后往前扫会先命中成交额，
      //   把 p[ti+2] 取成空串 → 涨跌幅 parseFloat('')=NaN → 美股格子永远不显示涨跌幅
      //   (2026-11-05 报障「写着实时却不更新」的根因)。
      let ti=-1;
      for(let i=p.length-1;i>=3;i--){
        if(/^20[0-9]{12}$/.test(p[i])||/^[0-9]{4}-[0-9]{2}-[0-9]{2}/.test(p[i])){ ti=i; break; }
      }
      if(ti>0){ pct=parseFloat(p[ti+2]); t=p[ti]; }
    }
    if(px==null||isNaN(px)) return;
    if(t&&!stamp) stamp=t;
    cells.push('<div class="cell"><div class="nm">'+esc(it.nm)+'<i>实时</i></div>'+
      '<div class="px">'+fmtPx(px)+
      (pct==null||isNaN(pct)?'':'<span class="ch '+qcls(pct)+'">'+
        (pct>0?'+':'')+pct.toFixed(2)+'%</span>')+'</div></div>');
  });
  // MSCI 全球医疗没有公开实时源：显示官方 EOD 收盘价，明确标「收盘」不冒充实时。
  // 更新时机写在下面的 stamp 里 —— 否则那个日期看起来像永远卡住不动。
  const h=(P.latest.assets||[]).filter(function(a){ return /医疗/.test(a.name); })[0];
  if(h&&h.price!=null){
    const md=String(h.price_date||'').slice(5);
    cells.push('<div class="cell"><div class="nm">MSCI 全球医疗<i>EOD'+(md?' '+md:'')+'</i></div>'+
      '<div class="px">'+fmtPx(h.price)+'</div></div>');
  }
  if(!cells.length){ box.style.display='none'; return; }
  box.style.display='';   // 之前失败被隐藏的，恢复显示（否则成功一次后永远看不见）
  // 「本次 HH:MM:SS」是刻意加的：页面挂在后台或接口静默失败时，这一行会停住不动，
  // 用户一眼就能看出「是没刷新」还是「刷新了但价格没变」。
  const nw = new Date();
  const at = ('0'+nw.getHours()).slice(-2)+':'+('0'+nw.getMinutes()).slice(-2)+
             ':'+('0'+nw.getSeconds()).slice(-2);
  const perDay = (P.schedule && P.schedule.tods) ? P.schedule.tods.length : 6;
  const body = cells.join('');
  // 价格没变就别重建 DOM。原来每 60 秒把 6 个格子整个 innerHTML 重写一遍，
  // 手机上会引起整条重排，页面正在滚动时会被"拽"一下 —— 用户感受就是「一直在刷新、很卡」。
  // 数据没变时只换掉「本次 HH:MM:SS」，证明确实拉过。
  const atEl = box.querySelector('.stamp i.now');
  if(body === _liveSig && atEl){
    atEl.textContent = at;
    return;
  }
  // ★ 价格变了也尽量别整条重建：交易时段几乎每分钟都有格子变价，
  //   整条 innerHTML 重写会让正在滚动的手机页面被"拽"一下（2026-11-04 报障）。
  //   格子数量没变（还是同一批标的）时走逐格更新，只替换价格变了的那一两格。
  const cur = box.querySelectorAll(':scope > .cell');
  if(_liveSig && atEl && cells.length && cur.length === cells.length){
    for(let i = 0; i < cells.length; i++){
      if(_liveCellHTML[i] !== cells[i]){
        cur[i].outerHTML = cells[i];
        _liveCellHTML[i] = cells[i];
      }
    }
    _liveSig = body;
    atEl.textContent = at;
    return;
  }
  _liveCellHTML = cells.slice();
  _liveSig = body;
  box.innerHTML = body+
    '<div class="stamp">'+
    '<span>行情时间 <b>'+(stamp?esc(stamp):'—')+
    '</b> · 腾讯行情每 60 秒刷新（本次 <i class="now">'+at+'</i>）</span>'+
    '<span>MSCI 全球医疗无实时源，用官方 <b>EOD 收盘</b>；每交易日 06:37 / 08:07 跑批时更新</span>'+
    '<span><b>实时价不参与打分</b>；分数、卡片收盘价、各类曲线每交易日 '+
    perDay+' 次整体重算</span></div>';
}

/* 指数技术位：当前价 + 涨跌幅 + 压力/支撑距离，跟着实时行情一起每分钟刷新。
   fib 7 条线在 payload 里（服务端算好），这里用实时价重新夹出上下最近的两条。 */
function renderSzK(){
  const SK = P.latest && P.latest.sz_kline;
  if(!SK || !SK.length) return;
  SK.forEach(function(sz){
    const raw = window['v_' + sz.symbol]; if(!raw) return;
    const p = String(raw).split('~');
    const px = parseFloat(p[3]);
    if(!px || isNaN(px)) return;
    if(!sz.fib) return;
    const sfx = sz.symbol;
    const setTxt = function(id, t){ const e=document.getElementById(id); if(e) e.textContent=t; };
    setTxt('szk-px-' + sfx, fmtPx(px));
    // 当日涨跌幅：A 股 14 位紧凑时间戳(20xx 开头)，涨跌幅在时间戳后两位（同 renderLive 口径）
    let ti=-1, pct=null;
    for(let i=p.length-1;i>=3;i--){
      if(/^20[0-9]{12}$/.test(p[i])||/^[0-9]{4}-[0-9]{2}-[0-9]{2}/.test(p[i])){ ti=i; break; }
    }
    if(ti>0) pct=parseFloat(p[ti+2]);
    const chgEl=document.getElementById('szk-chg-' + sfx);
    if(chgEl && pct!=null && !isNaN(pct)){
      chgEl.textContent=(pct>0?'+':'')+pct.toFixed(2)+'%';
      chgEl.className='chg '+(pct>0.0001?'up':(pct<-0.0001?'dn':'mid'));
    }
    const pctTxt = function(v){ if(v===0) return '0%'; if(v===1) return '100%'; return (v*100).toFixed(1)+'%'; };
    const num = function(v){ return Math.round(v).toLocaleString('zh-CN'); };
    let res=null, sup=null;
    sz.fib.forEach(function(f){
      if(f.price>px && (res===null || f.price<res.price)) res=f;
      if(f.price<px && (sup===null || f.price>sup.price)) sup=f;
    });
    if(res){
      setTxt('szk-res-p-' + sfx, pctTxt(res.pct));
      setTxt('szk-res-' + sfx, num(res.price));
      setTxt('szk-res-g-' + sfx, '+' + ((res.price-px)/px*100).toFixed(1) + '%');
    }
    if(sup){
      setTxt('szk-sup-p-' + sfx, pctTxt(sup.pct));
      setTxt('szk-sup-' + sfx, num(sup.price));
      setTxt('szk-sup-g-' + sfx, ((sup.price-px)/px*100).toFixed(1) + '%');
    }
  });
}
let _liveSig = '';
let _liveCellHTML = [];   // 上一轮每格的 HTML，用于逐格 diff，避免整条 innerHTML 重建
let _liveKill = null, _liveFail = 0, _liveNext = 0;
function loadLive(){
  if(document.hidden) return;
  if(Date.now() < _liveNext) return;          // 失败退避窗口内不再试
  if(_liveKill) return;                        // 上一发还没落地，别往上叠
  const s=document.createElement('script');
  s.charset='gbk';
  s.src='https://qt.gtimg.cn/q='+LIVE.map(function(x){return x.c;}).join(',')+'&_='+Date.now();
  // 每次调用都会新建一个 <script>。用完必须摘掉，否则一小时就攒 60 个节点，
  // 手机上内存和重排都吃不消（原来只建不删）。
  const drop=function(){
    if(_liveKill){ clearTimeout(_liveKill); _liveKill=null; }
    if(s.parentNode) s.parentNode.removeChild(s);
  };
  s.onload=function(){ drop(); _liveFail=0; _liveNext=0; renderLive(); renderSzK(); };
  s.onerror=function(){ drop(); _liveFail+=1;
    // 弱网退避：连败 1→1 分钟、2→5 分钟、≥3→15 分钟。
    // 原来每 60 秒硬拉、挂着不摘的 <script> 会占满手机连接池 —— 卡死主因之一。
    _liveNext=Date.now()+(_liveFail>=3?900000:(_liveFail===2?300000:60000));
    if(_liveFail>=2){ const b=document.getElementById('live'); if(b) b.style.display='none'; } };
  document.head.appendChild(s);
  // 8 秒硬超时：JSONP 弱网下可能永远不回调，原来节点一直挂着不摘、每分钟再叠一个。
  // 超时先补画一次（万一数据其实到了，renderLive 里有签名判断不会白画），再按失败处理。
  _liveKill=setTimeout(function(){ s.onerror(); }, 8000);
}

/* 二十二年那张图的窗口切换（服务端已生成好几份 SVG，这里只切显示） */
function bindEqw(){
  const roots=document.querySelectorAll('.eqw,.szk');
  Array.prototype.forEach.call(roots,function(root){
    const btns=root.querySelectorAll('.chartbar button');
    const panes=root.querySelectorAll('.sw');
    Array.prototype.forEach.call(btns,function(b){
      b.onclick=function(){
        Array.prototype.forEach.call(btns,function(x){ x.classList.remove('on'); });
        b.classList.add('on');
        Array.prototype.forEach.call(panes,function(p){
          p.hidden = (p.getAttribute('data-k')!==b.getAttribute('data-k'));
        });
      };
    });
  });
}

render();
bindEqw();
loadLive();
// 市场情绪直连 CNN。首次延迟 12 秒，别和首屏的几个请求抢带宽（后台时它自己会跳过）。
setTimeout(function(){ refreshMood(); }, 12000);
// 超短线擒龙：盘中每分钟直连东财。首次延迟 8 秒（非交易时段会自己跳过）。
setTimeout(function(){ refreshZhulong(); }, 8000);

const _narrow = (window.innerWidth || 1200) < 640;

/* ---------- 统一心跳 ----------
   原来三个 setInterval 各跑各的：移动端回前台瞬间所有定时器一起补触发，
   叠加页面恢复本身的渲染，就是「一切回来先卡一下」；后台时定时器仍会被
   浏览器周期性唤醒。现在只留一个 60 秒心跳，各任务按自己的周期节流：
   实时条 60s · CNN 情绪 60s（各自另带失败退避）· 新版本探测 窄屏 10min / 宽屏 3min。
   后台全停；回前台延迟 3 秒补一轮（避开恢复渲染高峰），30 秒内不重复补。 */
let _hbLive = 0, _hbMood = 0, _hbVer = 0, _hbZl = 0, _hbResume = 0;
const _VER_EVERY = _narrow ? 600000 : 180000;
function heartbeat(force){
  if(document.hidden) return;
  const now = Date.now();
  if(force){
    if(now - _hbResume < 30000) return;
    _hbResume = now;
  }
  if(now - _hbLive >= 60000){ _hbLive = now; loadLive(); }
  if(now - _hbMood >= 60000){ _hbMood = now; refreshMood(); }
  if(now - _hbZl >= 60000){ _hbZl = now; refreshZhulong(); }
  if(now - _hbVer >= _VER_EVERY){ _hbVer = now; checkNewer(); }
}
setInterval(function(){ heartbeat(false); }, 60000);
document.addEventListener('visibilitychange', function(){
  if(!document.hidden) setTimeout(function(){ heartbeat(true); }, 3000);
});
// iOS 从别的页面返回（bfcache 恢复）不一定触发 visibilitychange，这里补一刀
window.addEventListener('pageshow', function(e){
  if(e.persisted) setTimeout(function(){ heartbeat(true); }, 1500);
});

/* 页面是静态的：跑批在后台更新了 docs/data.json，但已经打开的页面还停在旧快照上。
   这里探一个极小的 ver.json（几十字节）来发现更新。
   ★ 别改回拉 data.json —— 它现在 270KB+，手机上每 3 分钟下一次，流量和解析开销都受不了，
     2026-10-31 用户报「手机端一直刷新很卡」，一个原因就是这个。
   file:// 下 fetch 会被同源策略拒绝，直接跳过（本地预览不需要这个提示）。 */
function checkNewer(){
  if(!/^https?:$/.test(location.protocol)) return;
  const cur = P.latest && P.latest.generated_at_ts;
  if(!cur) return;
  // ★「加载新数据」点过之后，GitHub Pages 的 CDN/浏览器缓存最长 10 分钟还在发旧的
  //   index.html —— 刷完版本号还是旧的，横条又弹出来 → 用户再点 → 再弹，
  //   看起来就是「页面莫名一直刷新」。点过一次后 10 分钟内不再提示，掐断这个循环。
  try{
    const rl = +sessionStorage.getItem('rl_ts') || 0;
    if(rl && Date.now() - rl < 600000) return;
  }catch(e){}
  fetch('ver.json?t=' + Date.now(), {cache:'no-store'})
    .then(function(r){ return r.ok ? r.json() : null; })
    .then(function(j){
      const t = j && j.ts;
      if(t && t > cur + 60){                       // 60 秒容差，避免同一次构建的抖动误报
        const nb = document.getElementById('newbar');
        if(!nb || !nb.hidden) return;              // 已经提示过就别重复写 DOM
        document.getElementById('newat').textContent = String(j.at||'').slice(11,16);
        document.getElementById('curat').textContent = String(P.latest.generated_at||'').slice(11,16);
        nb.hidden = false;
      }
    })
    .catch(function(){ /* 网络抖动/跨域失败都当没发生，不打扰用户 */ });
}
/* 点「加载新数据」：带唯一 query 强制绕过 GitHub Pages 的 CDN 缓存。
   之前用 location.reload()，CDN 最长 10 分钟还在发旧 index.html ——
   刷完版本号还是旧的，newbar 又弹、用户再点、再弹，看着像「页面一直自动刷新」。
   带 ?v=时间戳 让 CDN 把它当新 URL 回源，一次就能拿到最新版。 */
function loadNew(){
  try{ sessionStorage.setItem('rl_ts', Date.now()); }catch(e){}
  location.replace(location.pathname + '?v=' + Date.now());
}
// 首轮探测：窄屏延 60 秒、宽屏 20 秒；之后由心跳按 _VER_EVERY 节奏走。
if(!document.hidden){
  setTimeout(function(){ checkNewer(); _hbVer = Date.now(); }, _narrow ? 60000 : 20000);
}

// 横竖屏切换 / 窗口缩放时重画分数图（窄屏和宽屏用不同画布尺寸）。
// ★ 只在**宽度变了**才重画：手机上滚动时地址栏收起/展开改的是高度，innerWidth 不变，
//   原来无条件重画，等于每滚一下就把 5 条折线整张重算一遍 —— 卡顿的主因之一。
let _rz = null, _lastW = window.innerWidth;
window.addEventListener('resize', function(){
  if(window.innerWidth === _lastW) return;
  _lastW = window.innerWidth;
  clearTimeout(_rz);
  _rz = setTimeout(function(){ renderChart(); }, 200);
});
"""


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


# ---------------------------------------------------------------- 观察型模块
# 手绘 SVG：不用图表库（Pages 静态托管，外部 CDN 一旦被墙整页白屏）
def _svg(layers, w=520, h=210, log=False, refs=(), xlabels=(), pad=(46, 12, 18, 28),
         fs=10, ends=False):
    """多线折线图。layers=[{pts:[(idx, val)], color, width, dash}]，x 轴用索引。

    fs 是字号（用户单位）。窄屏画布用较大的 fs，因为它被缩小的倍数更少。
    ends=True 时在每条线的末端标出末值（白描边打底，压住线本身也能看清）。
    """
    import math

    allv = [v for L in layers for _i, v in L["pts"] if v] + [r[1] for r in refs]
    if not allv:
        return ""
    vmin, vmax = min(allv), max(allv)
    tf = (lambda v: math.log10(v)) if log else (lambda v: v)
    a, b = tf(vmin), tf(vmax)
    if b - a < 1e-9:
        b = a + 1.0
    n = max([len(L["pts"]) for L in layers] or [1])
    PL, PR, PT, PB = pad
    X = lambda i: PL + (w - PL - PR) * (i / max(1, n - 1))
    Y = lambda v: PT + (h - PT - PB) * (1 - (tf(v) - a) / (b - a))

    o = [f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">']
    # 对数轴用 1-2-3-5-7 优选刻度（等比、等距），线性轴均分四段
    if log:
        # 分档选取刻度：跨度大（22 年全貌）用 1-2-3-5-7 的粗刻度；
        # 跨度小（只看近 1 年）粗刻度常常只剩 1 根，得换成更细的 1.5/2.5/4/6/8
        ms = (1, 2, 3, 5, 7) if (vmax / max(vmin, 1e-9)) > 2.5 \
            else (1, 1.2, 1.4, 1.6, 1.8, 2, 2.2, 2.4, 2.6, 2.8, 3, 3.5,
                  4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5)
        ticks, p = [], int(math.floor(math.log10(max(vmin, 1e-9))))
        while 10 ** p <= vmax * 10:
            for mm in ms:
                v = mm * 10 ** p
                if vmin * 0.999 <= v <= vmax * 1.001:
                    ticks.append(v)
            p += 1
        if len(ticks) > 7:                  # 太密就隔一根取一根，末根必留
            thin = ticks[::2]
            if ticks[-1] not in thin:
                thin.append(ticks[-1])
            ticks = thin
        if len(ticks) < 2:
            ticks = [vmin, vmax]
    else:
        ticks = [vmin + (vmax - vmin) * k / 4.0 for k in range(5)]
    for v in ticks:
        yy = Y(v)
        txt = f"{v:,.0f}" if vmax >= 100 else f"{v:.2f}"
        o.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{w - PR}" y2="{yy:.1f}" '
                 'stroke="rgba(20,22,27,.11)" stroke-width="1"/>')
        o.append(f'<text x="{PL - 8}" y="{yy + 3.5:.1f}" fill="#6b6e78" font-size="{fs}" '
                 f'text-anchor="end">{txt}</text>')
    for lbl, rv, rc in refs:
        yy = Y(rv)
        o.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{w - PR}" y2="{yy:.1f}" stroke="{rc}" '
                 'stroke-width="1" stroke-dasharray="3 4"/>')
        # 标签放左侧起点上方：右下角会和小数点很多的 x 轴末标签撞在一起，
        # 右移 30px 是为了跟 y 轴刻度数字拉开，否则看起来像"0.30 参考 0.3"
        o.append(f'<text x="{PL + 30}" y="{yy - 6:.1f}" fill="{rc}" font-size="{fs + 0.5}" '
                 f'text-anchor="start" letter-spacing=".4">{lbl}</text>')
    for L in layers:
        seg = [(i, v) for i, v in L["pts"] if v]
        if not seg:
            continue
        d = " ".join(("M" if j == 0 else "L") + f"{X(i):.1f} {Y(v):.1f}"
                     for j, (i, v) in enumerate(seg))
        dash = f' stroke-dasharray="{L["dash"]}"' if L.get("dash") else ""
        o.append(f'<path d="{d}" fill="none" stroke="{L["color"]}" '
                 f'stroke-width="{L.get("width", 1.8)}"{dash} '
                 'stroke-linejoin="round" stroke-linecap="round"/>')
        if ends:
            li, lv = seg[-1]
            # 标在线的右端外侧（PR 已经留出 56 的空间），压在线上会盖住线尾
            o.append(f'<text x="{X(li) + 7:.1f}" y="{Y(lv) + fs * 0.35:.1f}" fill="{L["color"]}" '
                     f'font-size="{fs + 1}" font-weight="600" text-anchor="start" '
                     f'letter-spacing=".2">{lv:,.0f}</text>')
    # 横轴标签按像素去重：窄屏上「2025」「2026」只隔 17px，会叠成一坨。
    # 后一个挤到前一个身上就丢掉；如果后一个是「到现在」那根，反过来顶掉前一个。
    kept = []
    for i, txt in xlabels:
        xx = X(i)
        if kept and xx - kept[-1][0] < max(32, fs * 3.4):
            if i >= n - 1:
                kept[-1] = (xx, i, txt)
            continue
        kept.append((xx, i, txt))
    for xx, i, txt in kept:
        anchor = "start" if i == 0 else ("end" if i >= n - 1 else "middle")
        # 首个标签右移一点，避开 y 轴刻度数字（否则「0.30」和「2024-06-19」会粘在一起）。
        # 4 个字的年份标签只需挪 2px，挪 12px 会顶到后一年的标签上。
        if i == 0:
            xx = xx + (12 if len(txt) > 4 else 2)
        o.append(f'<text x="{xx:.1f}" y="{h - 6}" fill="#6b6e78" font-size="{fs}" '
                 f'text-anchor="{anchor}" letter-spacing=".3">{txt}</text>')
    o.append("</svg>")
    return "".join(o)


def _num(v, nd=2):
    return "—" if v is None else f"{v:,.{nd}f}"


def _xlabels(pts, maxn=6):
    """按窗口跨度自动选横轴标签：跨度 ≤ 14 个月用「年-月」，否则用整数年。

    年份刻度用 1/2/5/10 这种整数步长（不能出现 2004、2007、2010 这种怪间隔），
    步长从密到疏试，取第一个不超 maxn 的 —— 22 年全貌在宽屏上就是 2004…2026 每两年一个。
    """
    import datetime as _dt
    if not pts:
        return []
    try:
        span = (_dt.date.fromisoformat(pts[-1][0]) - _dt.date.fromisoformat(pts[0][0])).days
    except Exception:  # noqa: BLE001
        span = 0

    idx = {}
    if span <= 430:                     # 一年半以内 → 月份刻度
        for j, r in enumerate(pts):
            idx.setdefault(r[0][:7], j)
        keys = sorted(idx)
        step = max(1, (len(keys) - 1) // 4)
        pick = keys[::step]
        if pick[-1] != keys[-1]:
            pick.append(keys[-1])
        return [(idx[k], k[2:]) for k in pick]      # 2026-07 → 26-07

    for j, r in enumerate(pts):
        idx.setdefault(r[0][:4], j)
    yrs = sorted(idx)
    # 末年只走了几个月就别当刻度（会和前一根叠在一起）
    if len(yrs) > 2 and pts[-1][0][5:] < "09-30":
        yrs = yrs[:-1]
    step = 1
    for s in (1, 2, 5, 10, 20, 50):
        if sum(1 for y in yrs if int(y) % s == 0) <= maxn:
            step = s
            break
    cand = [y for y in yrs if int(y) % step == 0]
    if cand and yrs[0] not in cand and int(cand[0]) - int(yrs[0]) >= max(2, step - 1):
        cand.insert(0, yrs[0])          # 首年离第一个刻度太远才补，太近会叠字
    if yrs[-1] not in cand:
        cand.append(yrs[-1])
    return [(idx[y], y) for y in cand]


def _dev_html(dev, pct):
    """偏离百分比 + 分位的小标签：涨红跌绿（A 股习惯），分位低=便宜=绿。"""
    if dev is None:
        return "—"
    cls = "up" if dev > 0.5 else ("dn" if dev < -0.5 else "mid")
    tag = f'<i class="{cls}">{dev:+.2f}%</i>'
    if pct is not None:
        pc = "up" if pct > 70 else ("dn" if pct < 30 else "mid")
        tag += f'<i class="{pc}">历史分位 {pct:.0f}%</i>'
    return tag


def _nice_ticks(lo, hi, n=4):
    """把 [lo, hi] 切成整齐刻度（步长取 1/2/2.5/5 ×10^k）。

    为什么不用「均分四段」：均分出来是 -10.2% / -5.5% / -0.8% / +3.9% 这种读不出信息的数，
    而原值是「近一月涨跌」，读者只需要知道「大概跌了几个点」。
    """
    import math
    span = hi - lo
    if span <= 0:
        return [lo, hi]
    raw = span / max(1, n)
    p = 10 ** math.floor(math.log10(raw))
    step = 10 * p
    for m in (1, 2, 2.5, 5, 10):
        if m * p >= raw:
            step = m * p
            break
    v = math.ceil(lo / step) * step
    ticks = []
    while v <= hi + 1e-9:
        ticks.append(round(v, 6))
        v += step
    return ticks or [lo, hi]


def _pct_txt(v):
    """刻度标签：整数就不带小数点（+5% 而不是 +5.0%），小数才保留一位。"""
    return (f"{v:+.0f}%" if abs(v - round(v)) < 0.01 else f"{v:+.1f}%")


def _tw(s, fs):
    """粗略算一段文字有多宽（CJK/全角按 1em，ASCII 按 0.55em）。

    SVG 里量不到真实字宽（服务端渲染，没有 measureText），但这里只需要
    「给右侧留白留多少」这一个数，估得偏大一点反而安全（留白多点不会溢出）。
    """
    return sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in str(s)) * fs


def _chart_name(name):
    """末值标签用的名字：去掉括号里的补充说明。

    「黄金（COMEX 主力连续）」→「黄金」。右侧留白是按最长那个名字算的，
    留着一个 12 字的括号尾巴会把绘图区挤掉 1/10 的宽度。
    """
    s = re.sub(r"[（(][^）)]*[）)]", "", str(name))
    return " ".join(s.split()) or str(name)


def _ellip(s, fs, maxw):
    """名字超出可用宽度就截断加省略号 —— 宁可少两个字，也不能顶出 viewBox 被裁掉。"""
    s = str(s)
    if _tw(s, fs) <= maxw:
        return s
    out = ""
    for ch in s:
        if _tw(out + ch, fs) > maxw - _tw("…", fs):
            break
        out += ch
    return (out or s[:1]) + "…"


def _month_svg(items, w=1060, h=300, fs=10, maxx=6):
    """近一月累计涨跌对比图。**横轴按真实日期铺，不按数据点索引**。

    为什么不能用索引：各市场的交易日不同 —— 本期 A 股 17 个点、美股 23 个点
    （10 月长假让中证红利少了 6 天）。按索引画会把两条线压成同样长度，
    看着「同起点同终点」，实际时间跨度并不一样，这是最容易骗人的画法。

    items = [(name, month_dict, color), ...]
    """
    import datetime as dt

    ser = []
    for name, m, col in items:
        pts = []
        for p in m.get("pts") or []:
            try:
                pts.append((dt.date.fromisoformat(str(p[0])[:10]), float(p[1])))
            except (ValueError, TypeError):
                continue
        if len(pts) >= 4:
            ser.append((name, m, col, pts))
    if len(ser) < 2:
        return ""

    days = [d for _, _, _, pts in ser for d, _ in pts]
    d0, d1 = min(days), max(days)
    span = max(1, (d1 - d0).days)

    vals = [v for _, _, _, pts in ser for _, v in pts] + [0.0]
    vmin, vmax = min(vals), max(vals)
    if vmax - vmin < 1.5:            # 集体横盘时给个最小跨度，否则几条线糊成一根
        mid = (vmax + vmin) / 2
        vmin, vmax = mid - 0.75, mid + 0.75
    pad = (vmax - vmin) * 0.16
    ticks = _nice_ticks(vmin - pad, vmax + pad, 4)
    vmin, vmax = min(ticks[0], vmin - pad), max(ticks[-1], vmax + pad)

    # 右侧留白不再写死 54：末值标签现在要带指数名，按最长的那个名字算，
    # 否则「MSCI 全球医疗保健指数 +6.02%」会直接跑出画布被裁掉。
    # 窄画布（430 单位）一行放不下「名称 +x%」，改成名称在上、百分比在下两行。
    stack = w < 600
    nfs, pfs = fs, fs + 1            # 名称字号 / 百分比字号（百分比大一号、加粗）
    pctw = _tw("-88.88%", pfs)       # 按最宽的百分比 "-88.88%" 算，别按本期的实际值算
    room = max(54.0, w * 0.34)       # 右侧留白上限：再宽就把绘图区挤没了
    # 名字可用宽度 = 留白上限 − 线端点左偏 7 − 间距 −（一行模式还要减掉百分比）
    namecap = room - 12 - (0 if stack else 7 + 4 + pctw)
    names = [_ellip(_chart_name(n), nfs, namecap) for n, _m, _c, _p in ser]
    need = 0.0
    for nm in names:
        if stack:
            need = max(need, _tw(nm, nfs), pctw)
        else:
            need = max(need, 7 + _tw(nm, nfs) + 4 + pctw)
    # +12 = 标签相对线端点的左偏 7 加上安全余量，少了这几个单位字就顶出 viewBox
    PR = min(max(54.0, need + 12), room)
    PL, PT, PB = (40 if stack else 50), 18, 26
    X = lambda d: PL + (w - PL - PR) * ((d - d0).days / span)
    Y = lambda v: PT + (h - PT - PB) * (1 - (v - vmin) / (vmax - vmin))

    o = [f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">']

    # 近 7 天竖带（各标的 week_from 最多差一天，取最早的做统一边界）
    try:
        wk = min(dt.date.fromisoformat(str(m["week_from"])[:10])
                 for _, m, _, _ in ser if m.get("week_from"))
    except ValueError:
        wk = d1
    xw = X(wk)
    if d1 > wk:
        o.append(f'<rect x="{xw:.1f}" y="{PT}" width="{X(d1) - xw:.1f}" '
                 f'height="{h - PT - PB}" fill="rgba(20,22,27,.055)"/>')
        o.append(f'<line x1="{xw:.1f}" y1="{PT}" x2="{xw:.1f}" y2="{h - PB}" '
                 'stroke="rgba(20,22,27,.18)" stroke-width="1" stroke-dasharray="3 4"/>')
        if X(d1) - xw > fs * 5.4:
            o.append(f'<text x="{(xw + X(d1)) / 2:.1f}" y="{PT - 6}" fill="#6b6e78" '
                     f'font-size="{fs}" text-anchor="middle" letter-spacing=".9">近 7 天</text>')

    for v in ticks:
        yy = Y(v)
        o.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{w - PR}" y2="{yy:.1f}" '
                 'stroke="rgba(20,22,27,.09)" stroke-width="1"/>')
        o.append(f'<text x="{PL - 8}" y="{yy + 3.5:.1f}" fill="#6b6e78" font-size="{fs}" '
                 f'text-anchor="end">{_pct_txt(v)}</text>')

    if vmin < 0 < vmax:              # 0% = 窗口起点，涨跌分水岭
        o.append(f'<line x1="{PL}" y1="{Y(0):.1f}" x2="{w - PR}" y2="{Y(0):.1f}" '
                 'stroke="rgba(20,22,27,.32)" stroke-width="1" stroke-dasharray="5 4"/>')

    for name, m, col, pts in ser:
        d = " ".join(("M" if i == 0 else "L") + f"{X(dd):.1f} {Y(v):.1f}"
                     for i, (dd, v) in enumerate(pts))
        o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" '
                 'stroke-linejoin="round" stroke-linecap="round"/>')

    # 末值标签单独一轮画：两条线末端靠得近时会糊成一坨（本期纳指综合 -4.10% 与
    # 纳指100 -5.00% 只差 0.9 个点 ≈ 13px），先按 y 排序再逐个压开最小间距。
    # 标签带指数名（原来是光秃秃的 +6.02%，读者对不上是哪条线）。
    ends = sorted((Y(pts[-1][1]), pts[-1][1], col, X(pts[-1][0]), nm)
                  for (_n, _m, col, pts), nm in zip(ser, names))
    bh = (nfs * 1.16 + pfs * 1.16) if stack else pfs * 1.25   # 单个标签块的高度
    # 两行模式下块与块之间要多留一截：名字和它自己的百分比贴紧、跟邻居拉开，
    # 否则「上一块的数字」看着像「下一块的名字」——正是这次要修的那个毛病。
    # 一行模式给 1.32 倍：相邻两块的数字常只差 1 分多（45.8 / 44.6），1.16 倍贴得太死。
    gap = bh * (1.5 if stack else 1.32)
    fixed, prev = [], None
    for y, lv, col, xx, nm in ends:
        if prev is not None and y - prev < gap:
            y = prev + gap
        fixed.append((y, lv, col, xx, nm))
        prev = y
    over = (fixed[-1][0] + bh / 2) - (h - PB + fs * 0.55)
    if over > 0:                     # 推到底边外就整组上移
        fixed = [(y - over, lv, col, xx, nm) for y, lv, col, xx, nm in fixed]
    top = (fixed[0][0] - bh / 2) - 2
    if top < 0:                      # 上移过头顶到画布外，再整组压回来
        fixed = [(y - top, lv, col, xx, nm) for y, lv, col, xx, nm in fixed]
    # 被压开的标签画一小段引线连回真实端点：不然标签看着像标到了旁边那条线上。
    # ends 与 fixed 顺序一致（只按 y 排过一次，后面全是整体平移），可以 zip。
    for (y0, _lv, col, xx, _nm), (y, _a, _b, _c, _d) in zip(ends, fixed):
        if abs(y - y0) > 0.5:
            o.append(f'<path d="M{xx + 2:.1f} {y0:.1f}L{xx + 6:.1f} {y:.1f}" fill="none" '
                     f'stroke="{col}" stroke-width="1" stroke-opacity=".45"/>')
    for y, lv, col, xx, nm in fixed:
        if stack:
            o.append(f'<text x="{xx + 7:.1f}" y="{y - bh / 2 + nfs * 0.95:.1f}" '
                     f'fill="{col}" fill-opacity=".78" font-size="{nfs}" '
                     'text-anchor="start" paint-order="stroke fill" stroke="#fff" '
                     f'stroke-width="2.6" stroke-linejoin="round">{_esc(nm)}</text>')
            o.append(f'<text x="{xx + 7:.1f}" y="{y + bh / 2 - pfs * 0.22:.1f}" '
                     f'fill="{col}" font-size="{pfs}" font-weight="600" '
                     'text-anchor="start" paint-order="stroke fill" stroke="#fff" '
                     f'stroke-width="3" stroke-linejoin="round">{lv:+.2f}%</text>')
        else:
            # 名称与百分比放同一个 <text> 里（两个 tspan）：位置交给排版引擎算，
            # 不用自己估字宽去摆第二个 —— 估错了两个就叠在一起了。
            o.append(f'<text x="{xx + 7:.1f}" y="{y + fs * 0.35:.1f}" '
                     'text-anchor="start" paint-order="stroke fill" stroke="#fff" '
                     f'stroke-width="3" stroke-linejoin="round">'
                     f'<tspan fill="{col}" fill-opacity=".78" font-size="{nfs}">{_esc(nm)}</tspan>'
                     f'<tspan dx="4" fill="{col}" font-size="{pfs}" '
                     f'font-weight="600">{lv:+.2f}%</tspan></text>')

    # 横轴：首尾必标，中间按自然日等分（不按数据点等分）
    xl = [(d0, d0.strftime("%m-%d")), (d1, d1.strftime("%m-%d"))]
    for i in range(1, max(1, maxx - 1)):
        dd = d0 + dt.timedelta(days=round(span * i / float(maxx - 1)))
        if d0 < dd < d1:
            xl.append((dd, dd.strftime("%m-%d")))
    for dd, txt in sorted(set(xl)):
        anchor = "start" if dd == d0 else ("end" if dd == d1 else "middle")
        xx = X(dd) + (2 if dd == d0 else 0)
        o.append(f'<text x="{xx:.1f}" y="{h - 8}" fill="#6b6e78" font-size="{fs}" '
                 f'text-anchor="{anchor}" letter-spacing=".3">{txt}</text>')

    o.append("</svg>")
    return "".join(o)


# 每个标的固定一个颜色（不按数组顺序轮）：黄金是金色、红利是砖红，读者看图例就能对上线。
# 顺序轮换的话，以后在 config 里插一个标的，后面所有线的颜色都会跟着平移，历史印象全乱。
MONTH_COLORS = {
    "IXIC": "#111827",
    "NDX": "#2f6fb0",
    "GOLD": "#a8752a",
    "MSCI_HEALTH": "#2f7d5e",
    "CSI_DIVIDEND": "#b4512f",
}
MONTH_FALLBACK = ["#5b4b8a", "#7a7f8c", "#3f7f9e", "#8a6b25", "#9c4f4f"]


def _month_html(latest):
    """近一月涨跌板块（价格口径，**不参与打分**）。两个以上标的才画。"""
    assets = [a for a in (latest.get("assets") or []) if a.get("month")]
    if len(assets) < 2:
        return ""
    items = []
    for i, a in enumerate(assets):
        col = MONTH_COLORS.get(a["id"]) or MONTH_FALLBACK[i % len(MONTH_FALLBACK)]
        items.append((a["name"], a["month"], col))

    wide = _month_svg(items, w=1060, h=310, fs=10, maxx=6)
    # 窄画布抬高一点：末值标签改成两行（名称在上、百分比在下），5 个标的要竖着排开
    narrow = _month_svg(items, w=430, h=330, fs=11, maxx=3)
    if not wide:
        return ""

    legs = "".join(
        '<span class="mleg"><i style="background:%s"></i><em class="n">%s</em>'
        '<b class="%s">%+.2f%%</b><em>7 日 %+.2f%%</em></span>'
        % (c, _esc(n), "up" if m["chg_month"] >= 0 else "dn",
           m["chg_month"], m["chg_week"])
        for n, m, c in items)

    ends = sorted({str(a["month"].get("end_date") or "")[5:10] for a in assets})
    wks = sorted({str(a["month"].get("week_from") or "")[5:10] for a in assets})
    # 别在 f-string 里写嵌套引号的表达式（Python 3.12 之前是语法错误，Actions 上的版本不确定）
    ends_txt = "、".join(ends)
    wks_txt = "、".join(wks)
    cap = (f"截止 {ends_txt}　·　近 7 天从 {wks_txt} 起　·　"
           "各市场交易日不同，横轴按真实日期铺，不按数据点等分")

    return f"""<div class="chart mchart">
  <div class="mhead">
    <div class="t">近一月累计涨跌</div>
    <div class="sub">以窗口首日收盘为 0%　·　<b>价格口径，不是分数</b>　·　
      右侧灰底 = 最近 7 个自然日</div>
  </div>
  <div class="mlegs">{legs}</div>
  <div class="v-w">{wide}</div>
  <div class="v-n">{narrow}</div>
  <div class="cap">{_esc(cap)}</div>
</div>"""


# 深证成指技术位：K 线配色。A 股「涨红跌绿」，阳线红、阴线绿。
SZ_UP = "#c43d2e"       # 阳线（收盘 ≥ 开盘，涨）
SZ_DN = "#2f7d54"       # 阴线（收盘 < 开盘，跌）
SZ_FIB = "#c9a227"      # 斐波那契回调线（黄）
SZ_FIB_BND = "#d8c06a"  # 0%/100% 边界（浅黄，弱化）
SZ_CUR = "#14161b"      # 当前价参考线


def _sz_fib_pct(p):
    if p == 0.0:
        return "0%"
    if p == 1.0:
        return "100%"
    return f"{p*100:.1f}%"


def _sz_kline_svg(sz, w, h, fs=9.5, klines=None):
    """深成指日 K + 斐波那契回调线 SVG。

    蜡烛用 4 个 path 合并画（阳影线 / 阴影线 / 阳实体 / 阴实体），
    660 根蜡烛只产生 4 个 <path>，避免单根一个 <rect>+<line> 把 SVG 撑到上百 KB。

    klines：传入时表示只画这一段日 K（日期切换功能），Y 轴按这段自适应；
    默认（None）画全量。自适应范围会把「压力 / 支撑」两条线一起包进去，
    保证它们永远落在图内。
    """
    if klines is None:
        klines = sz.get("klines") or []
    fib = sz.get("fib") or []
    cur = sz["cur"]
    res = sz.get("resistance") or {}
    sup = sz.get("support") or {}
    n = len(klines)
    if n < 2:
        return ""

    # Y 轴按「这段 K 线的高低」自适应，并把压力/支撑线一起纳入，确保可见。
    lo = min(k["l"] for k in klines)
    hi = max(k["h"] for k in klines)
    for _p in (res.get("price"), sup.get("price")):
        if _p is not None:
            lo = min(lo, _p)
            hi = max(hi, _p)
    pad = (hi - lo) * 0.06
    ymin, ymax = lo - pad, hi + pad

    PL = 66 if w >= 600 else 72          # 左留白：放斐波那契「百分比 + 价格」（窄屏字号大、价格带千分位，留宽点）
    PR = 52 if w >= 600 else 40          # 右留白：放价格刻度
    PT, PB = 14, 24
    pw = w - PL - PR
    ph = h - PT - PB
    cw = pw / n
    bw = min(3.0, max(0.7, cw * 0.66))
    X = lambda i: PL + pw * (i + 0.5) / n
    Y = lambda v: PT + ph * (1 - (v - ymin) / (ymax - ymin))

    o = [f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">']

    # 网格 + 右侧价格刻度
    for v in _nice_ticks(ymin, ymax, 5):
        yy = Y(v)
        o.append(f'<line x1="{PL}" y1="{yy:.1f}" x2="{w-PR}" y2="{yy:.1f}" '
                 'stroke="rgba(20,22,27,.07)" stroke-width="1"/>')
        o.append(f'<text x="{w-PR+5}" y="{yy+3:.1f}" fill="#8a8d95" font-size="{fs-0.5}" '
                 f'text-anchor="start">{v:,.0f}</text>')

    # 蜡烛：影线 + 实体，按涨跌各合并成一个 path
    wick_u, wick_d, body_u, body_d = [], [], [], []
    for i, k in enumerate(klines):
        x = X(i)
        seg = f"M{x:.1f} {Y(k['h']):.1f}V{Y(k['l']):.1f}"
        y_top = Y(max(k["o"], k["c"]))
        y_bot = Y(min(k["o"], k["c"]))
        bh = max(1.0, y_bot - y_top)
        x0 = x - bw / 2
        box = f"M{x0:.1f} {y_top:.1f}h{bw:.1f}v{bh:.1f}h-{bw:.1f}z"
        if k["c"] >= k["o"]:
            wick_u.append(seg)
            body_u.append(box)
        else:
            wick_d.append(seg)
            body_d.append(box)
    if wick_u:
        o.append(f'<path d="{"".join(wick_u)}" fill="none" stroke="{SZ_UP}" stroke-width="0.7"/>')
    if wick_d:
        o.append(f'<path d="{"".join(wick_d)}" fill="none" stroke="{SZ_DN}" stroke-width="0.7"/>')
    if body_u:
        o.append(f'<path d="{"".join(body_u)}" fill="{SZ_UP}" stroke="{SZ_UP}" stroke-width="0.3"/>')
    if body_d:
        o.append(f'<path d="{"".join(body_d)}" fill="{SZ_DN}" stroke="{SZ_DN}" stroke-width="0.3"/>')

    # 斐波那契线：0%/100% 边界弱化，5 条中间线黄色；压力/支撑线加粗高亮
    res_p = res.get("price")
    sup_p = sup.get("price")
    for f in fib:
        y = Y(f["price"])
        # 短窗口下落在可视范围之外的斐波那契线直接不画（连标签也不画），
        # 避免一堆线 + 文字堆在图的上下边界外。
        if y < PT - 4 or y > PT + ph + 4:
            continue
        is_res = res_p is not None and abs(f["price"] - res_p) < 1e-6
        is_sup = sup_p is not None and abs(f["price"] - sup_p) < 1e-6
        if is_res:
            col, wd = "#b4452e", 1.7
        elif is_sup:
            col, wd = "#2f7d54", 1.7
        elif f["pct"] in (0.0, 1.0):
            col, wd = SZ_FIB_BND, 1.0
        else:
            col, wd = SZ_FIB, 1.2
        dash = ' stroke-dasharray="4 3"' if f["pct"] in (0.0, 1.0) else ''
        o.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{w-PR}" y2="{y:.1f}" '
                 f'stroke="{col}" stroke-width="{wd}"{dash}/>')
        # 左侧标注：百分比（金/红/绿）+ 价格（灰）。压力/支撑线只靠颜色+加粗区分，
        # 不再叠「压力/支撑」文字标签 —— 顶部提示条已写清「上方压力 / 下方支撑」，
        # 图上再叠一行字会跟百分比+价格压在一起（2026-11-04 截图发现的重叠）。
        pct_col = "#b4452e" if is_res else ("#2f7d54" if is_sup else "#a08030")
        o.append(f'<text x="{PL-5}" y="{y+3:.1f}" text-anchor="end" font-size="{fs}">'
                 f'<tspan fill="{pct_col}" font-weight="{600 if (is_res or is_sup) else 400}">'
                 f'{_sz_fib_pct(f["pct"])}</tspan>'
                 f'<tspan dx="3" fill="#6b6e78">{f["price"]:,.0f}</tspan></text>')

    # 当前价参考线（最新收盘价；实时价在顶部提示条每分钟刷新）
    y_cur = Y(cur)
    o.append(f'<line x1="{PL}" y1="{y_cur:.1f}" x2="{w-PR}" y2="{y_cur:.1f}" '
             f'stroke="{SZ_CUR}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    cur_lbl = f"最新 {cur:,.2f}" if w >= 600 else f"{cur:,.2f}"
    o.append(f'<text x="{w-PR-3}" y="{y_cur-6:.1f}" text-anchor="end" fill="{SZ_CUR}" '
             f'font-size="{fs if w >= 600 else fs-0.5}" font-weight="600">{cur_lbl}</text>')

    # 日期轴：只标这段 K 线的首尾；swing 高点若落在段内（宽屏）再补一个中间标记。
    import datetime as _dt
    def _d(s):
        return _dt.date.fromisoformat(str(s)[:10])
    d0, d1 = _d(klines[0]["d"]), _d(klines[-1]["d"])
    hd = _d(sz["swing_high"]["date"])
    fmt = "%y-%m-%d" if w >= 600 else "%y-%m"
    span = max(1, (d1 - d0).days)
    marks = [(d0, "start"), (d1, "end")]
    if w >= 600 and d0 <= hd <= d1:
        marks.insert(1, (hd, "mid"))
    for dd, mode in marks:
        frac = (dd - d0).days / span
        xx = PL + pw * frac
        anchor = "start" if mode == "start" else ("end" if mode == "end" else "middle")
        o.append(f'<text x="{xx:.1f}" y="{h-8}" fill="#6b6e78" font-size="{fs}" '
                 f'text-anchor="{anchor}">{dd.strftime(fmt)}</text>')

    o.append("</svg>")
    return "".join(o)


def _sz_kline_html(sz):
    """单个指数的技术位板块。sz 为 None 时返回空串（整段不输出）。"""
    if not sz or not sz.get("fib"):
        return ""
    sfx = sz["symbol"]          # 用作 DOM id 后缀，保证四个指数互不冲突
    nm = sz.get("name") or sfx  # 注意：下面日期窗口循环的循环变量也叫 name，这里必须用别的名字
    res = sz.get("resistance") or {}
    sup = sz.get("support") or {}
    cur = sz["cur"]
    klines_all = sz.get("klines") or []

    def _gap(f, cur_):
        if not f:
            return None
        return (f["price"] - cur_) / cur_ * 100

    res_gap = _gap(res, cur)
    sup_gap = _gap(sup, cur)

    # 日期切换：按交易日窗口切成多份 SVG，前端只切显隐（复用 bindEqw 的 .chartbar/.sw）。
    # 默认「近 1 年」——蜡烛够宽、不拥挤；切「全部」看完整 0%~100% 斐波那契。
    wins = [("1m", "近 1 月", 22),
            ("3m", "近 3 月", 66),
            ("6m", "近 6 月", 132),
            ("1y", "近 1 年", 250),
            ("all", "全部", None)]

    btns, panes = [], []
    for k, name, cnt in wins:
        kl = klines_all if cnt is None else klines_all[-cnt:]
        if len(kl) < 2:
            continue
        wide = _sz_kline_svg(sz, w=1060, h=360, fs=9.5, klines=kl)
        narrow = _sz_kline_svg(sz, w=430, h=380, fs=10.5, klines=kl)
        if not wide:
            continue
        on = (k == "1y")
        cls = ' class="on"' if on else ""
        btns.append(f'<button type="button" data-k="{k}"{cls}>{name}</button>')
        panes.append(f'<div class="sw" data-k="{k}"{"" if on else " hidden"}>'
                     f'<div class="v-w">{wide}</div>'
                     f'<div class="v-n">{narrow}</div></div>')
    if not panes:
        return ""

    res_pct = _sz_fib_pct(res["pct"]) if res else "—"
    res_price = f'{res["price"]:,.0f}' if res else "—"
    res_gap_t = f'{res_gap:+.1f}%' if res_gap is not None else "—"
    sup_pct = _sz_fib_pct(sup["pct"]) if sup else "—"
    sup_price = f'{sup["price"]:,.0f}' if sup else "—"
    sup_gap_t = f'{sup_gap:+.1f}%' if sup_gap is not None else "—"

    # 斐波那契锚点一句话：让读者知道这套线从哪来、会不会变
    anchor_txt = (f'斐波那契取「{sz["swing_low"]["date"]} 低点 {sz["swing_low"]["price"]:,.0f}」'
                  f'→「{sz["swing_high"]["date"]} 高点 {sz["swing_high"]["price"]:,.0f}」，'
                  f'未来创新高/新低会自动重画')

    return f"""<div class="szk chart">
  <div class="mhead">
    <div class="t">{_esc(nm)} · 技术位</div>
    <div class="sub">斐波那契回调 · 黄色分界线 = 23.6% / 38.2% / 50% / 61.8% / 80.9%　·　
      当前价夹在「支撑 / 压力」之间，涨跌幅与距离每分钟随实时价刷新</div>
  </div>
  <div class="szk-top">
    <div class="szk-now"><span class="lbl">{_esc(nm)}</span><b id="szk-px-{sfx}">{cur:,.2f}</b><span class="chg mid" id="szk-chg-{sfx}">—</span><span class="rt">实时</span></div>
    <div class="res"><span class="lbl">上方压力</span><span class="pct" id="szk-res-p-{sfx}">{_esc(res_pct)}</span><b id="szk-res-{sfx}">{_esc(res_price)}</b><span class="gap" id="szk-res-g-{sfx}">{_esc(res_gap_t)}</span></div>
    <div class="sup"><span class="lbl">下方支撑</span><span class="pct" id="szk-sup-p-{sfx}">{_esc(sup_pct)}</span><b id="szk-sup-{sfx}">{_esc(sup_price)}</b><span class="gap" id="szk-sup-g-{sfx}">{_esc(sup_gap_t)}</span></div>
  </div>
  <div class="chartbar"><div class="btns">{''.join(btns)}</div>
    <div class="delta"><span class="lb">日频数据</span>点击切换日期范围 · 「全部」看完整 0%~100% 斐波那契</div></div>
  {''.join(panes)}
  <div class="cap">{_esc(anchor_txt)}　·　当前价/压力/支撑距离为实时（腾讯行情每 60 秒），
      K 线为日频、随跑批刷新</div>
</div>"""


def _sz_kline_sections(sz_list):
    """多个指数的技术位板块拼接。空/None 返回空串。"""
    if not sz_list:
        return ""
    return "".join(_sz_kline_html(sz) for sz in sz_list if sz and sz.get("fib"))


def _zhulong_html(zl):
    """超短线擒龙板块。zl 为 None / empty 时返回空串（整段不输出）。

    纯展示、不参与打分。数据日频（东财涨停板池），盘前 09:15 跑批时自动回退到
    上一交易日（= 昨日复盘 / 连板梯队），盘后 15:17 是当日全天数据。
    """
    if not zl or not isinstance(zl, dict):
        return ""
    if zl.get("empty"):
        return ('<div class="zl chart"><div class="mhead">'
                '<div class="t">超短线擒龙</div>'
                '<div class="sub">本期未取到涨停板池数据（长假或接口不可用），板块暂不展示</div>'
                '</div></div>')

    mkt = zl.get("market") or {}
    # as_of 是 API 的 qdate（20261105），统一转成可读格式
    _d = str(zl.get("as_of") or "")
    as_of = f"{_d[:4]}-{_d[4:6]}-{_d[6:8]}" if len(_d) == 8 else _d

    # ---- 盘面概览 ----
    def _st(lbl, val, cls=""):
        return (f'<div class="st"><span class="lbl">{lbl}</span>'
                f'<b class="{cls}">{_esc(val)}</b></div>')

    stats = ('<div class="zl-stats">'
             + _st("涨停", mkt.get("zt", "—"), "up")
             + _st("炸板", mkt.get("zb", "—"))
             + _st("跌停", mkt.get("dt", "—"), "dn")
             + _st("最高板", f"{mkt.get('max_lbc', 0)}连板" if mkt.get("max_lbc") else "—")
             + '</div>')

    # ---- 按题材分组的领涨/补涨龙头卡（精简到每题材最强） ----
    def _conf_cls(txt):
        return {"高": "cf cf-hi", "中": "cf cf-mid", "低": "cf cf-lo"}.get(txt, "cf cf-mid")

    def _pick_row(label, badge_cls, p):
        if not p:
            return (f'<div class="zp-row empty"><span class="zp-role {badge_cls}">{label}</span>'
                    '<span class="zp-none">本期无</span></div>')
        buy_cls = " buyable" if p.get("buyable") else ""
        buy_tag = '<span class="zp-buy-tag">买</span>' if p.get("buyable") else ""
        conf = p.get("conf") or ""
        cf = (f'<span class="{_conf_cls(conf)}">可信·{_esc(conf)}</span>' if conf else "")
        label_txt = f'{_esc(p["label"])} · ' if p.get("label") else ""
        fund_txt = f' · 封单 {_esc(p.get("fund") or "—")}' if p.get("lbc") else ""
        return (f'<div class="zp-row{buy_cls}">'
                f'<span class="zp-role {badge_cls}">{label}</span>'
                f'<div class="zp-info">'
                f'<div class="zp-nm">{_esc(p["name"])}<span class="zp-cd">{_esc(p["code"])}</span></div>'
                f'<div class="zp-meta">{label_txt}涨幅 <span class="up">{p["chg"]:+.2f}%</span>'
                f'{fund_txt} · 换手 {p.get("hs", 0):.1f}%</div>'
                f'<div class="zp-rs">{_esc(p["reason"])}</div>'
                f'</div>{cf}{buy_tag}</div>')

    pick_cards = []
    for pk in (zl.get("picks") or []):
        lead = _pick_row("领涨龙头", "lead", pk.get("leader"))
        cu = _pick_row("补涨龙头", "cu", pk.get("catchup"))
        pick_cards.append(
            f'<div class="zp-card">'
            f'<div class="zp-hd">{_esc(pk["theme"])}<span class="zp-cnt">{pk["count"]}家涨停</span></div>'
            f'{lead}{cu}'
            f'</div>')
    picks_html = ""
    if pick_cards:
        picks_html = ('<div class="zl-picks">'
                      '<div class="hd">按题材分组 · 领涨/补涨龙头 '
                      '<span class="hint">每个热点题材只留最强的两只 · 可买标红 + 红色「买」字</span></div>'
                      '<div class="zp-grid">' + ''.join(pick_cards) + '</div>'
                      '</div>')

    # ---- 题材温度（概念涨幅榜） ----
    chips = []
    for c in (zl.get("concepts") or [])[:8]:
        chips.append(f'<span class="chip">{_esc(c["name"])} <b>{c["chg"]:+.2f}%</b></span>')
    tags = ('<div class="zl-tags"><span class="tagk">题材温度</span>'
            + ''.join(chips)
            + ('</div>' if chips else '<span class="hint">—</span></div>'))

    # ---- 热点题材榜（涨停家数聚合） ----
    theme_rows = []
    for t in (zl.get("themes") or [])[:8]:
        theme_rows.append(
            '<tr>'
            f'<td class="nm">{_esc(t["name"])}</td>'
            f'<td class="r up"><b>{t["count"]}</b></td>'
            f'<td class="r">{t["max_lbc"]}板</td>'
            f'<td class="dim">{_esc(t["leader"] or "—")}</td>'
            '</tr>')
    themes_html = ""
    if theme_rows:
        themes_html = (
            '<div class="zl-ct">热点题材榜 <span class="hint">按涨停家数计 · 涨停潮所在 = 题材所在</span></div>'
            '<div class="zl-scroll"><table class="zl-tbl">'
            '<thead><tr><th>题材(行业)</th><th class="r">涨停家数</th>'
            '<th class="r">最高板</th><th>龙头</th></tr></thead>'
            '<tbody>' + ''.join(theme_rows) + '</tbody></table></div>')

    # ---- 龙头梯队（连板 >= 2） ----
    def _badge(row):
        lbc = row.get("lbc") or 0
        cls = "zl-badge" if lbc >= 3 else "zl-badge gold"
        return f'<span class="{cls}">{_esc(row.get("label") or "首板")}</span>'

    dragon_rows = []
    for d in (zl.get("dragon") or [])[:15]:
        cyc = (f' <span class="zl-badge cycle">{_esc(d["cycle"])}</span>'
               if d.get("cycle") else "")
        dragon_rows.append(
            '<tr>'
            f'<td class="nm">{_esc(d["name"])}<span class="cd"> {_esc(d["code"])}</span></td>'
            f'<td>{_badge(d)}{cyc}</td>'
            f'<td class="dim">{_esc(d.get("hybk") or "—")}</td>'
            f'<td class="r dim">{_esc(d.get("fbt") or "—")}</td>'
            f'<td class="r">{_esc(d.get("fund") or "—")}</td>'
            f'<td class="r dim">{d.get("hs", 0):.1f}%</td>'
            '</tr>')
    dragon_html = ""
    if dragon_rows:
        dragon_html = (
            '<div class="zl-ct">龙头梯队 <span class="hint">连板 ≥ 2 · 最高板 = 空间龙头</span></div>'
            '<div class="zl-scroll"><table class="zl-tbl">'
            '<thead><tr><th>名称</th><th>连板</th><th>行业</th>'
            '<th class="r">封板</th><th class="r">封单</th><th class="r">换手</th></tr></thead>'
            '<tbody>' + ''.join(dragon_rows) + '</tbody></table></div>')

    # ---- 异动监控（炸板池） ----
    zb_rows = []
    for z in (zl.get("zhaban") or [])[:10]:
        chg = z.get("chg") or 0
        chg_cls = "up" if chg > 0 else ("dn" if chg < 0 else "dim")
        chg_txt = f'{chg:+.2f}%'
        zb_rows.append(
            '<tr>'
            f'<td class="nm">{_esc(z["name"])}<span class="cd"> {_esc(z["code"])}</span></td>'
            f'<td><span class="zl-badge zb">炸板{z.get("zbc") or 0}次</span>'
            + (f' <span class="zl-badge cycle">{_esc(z["cycle"])}</span>' if z.get("cycle") else "")
            + '</td>'
            f'<td class="r dim">{z.get("zf") if z.get("zf") is not None else "—"}%</td>'
            f'<td class="r dim">{z.get("hs", 0):.1f}%</td>'
            f'<td class="r {chg_cls}">{z.get("price", 0):.2f} ({chg_txt})</td>'
            '</tr>')
    zb_html = ""
    if zb_rows:
        zb_html = (
            '<div class="zl-ct">异动监控 <span class="hint">炸板 = 涨停后打开 · 龙头分歧信号</span></div>'
            '<div class="zl-scroll"><table class="zl-tbl">'
            '<thead><tr><th>名称</th><th>状态</th><th class="r">振幅</th>'
            '<th class="r">换手</th><th class="r">现价</th></tr></thead>'
            '<tbody>' + ''.join(zb_rows) + '</tbody></table></div>')
    if not zb_rows:
        zb_html = ('<div class="zl-ct">异动监控 <span class="hint">今日无炸板，封板情绪强</span></div>'
                   '<div class="zl-zb-note">涨停板池中炸板次数均为 0。</div>')

    # ---- 补涨候选 ----
    cu_rows = []
    for c in (zl.get("catchup") or [])[:12]:
        cu_rows.append(
            '<tr>'
            f'<td class="nm">{_esc(c["name"])}<span class="cd"> {_esc(c["code"])}</span></td>'
            f'<td class="dim">{_esc(c["theme"])}</td>'
            f'<td class="r up">{c["chg"]:+.2f}%</td>'
            f'<td class="r dim">{c.get("hs", 0):.1f}%</td>'
            '</tr>')
    cu_html = ""
    if cu_rows:
        cu_html = (
            '<div class="zl-ct">补涨候选 <span class="hint">热点题材中 · 今日上涨但未封板 · 龙头高位后的接力/补涨观察</span></div>'
            '<div class="zl-scroll"><table class="zl-tbl">'
            '<thead><tr><th>名称</th><th>题材</th><th class="r">涨幅</th>'
            '<th class="r">换手</th></tr></thead>'
            '<tbody>' + ''.join(cu_rows) + '</tbody></table></div>')
    else:
        cu_html = ('<div class="zl-ct">补涨候选 <span class="hint">本期未取到（行业成分接口不可用）</span></div>')

    # ---- 方法论（AI短剧 + 创新药 案例复盘） ----
    method = (
        '<div class="zl-method">'
        '<div class="t">构造逻辑 · 从两个真实题材案例提炼</div>'
        '<ol>'
        '<li><b>找题材</b>：题材按「涨停家数」计 —— 某板块出现 3~5 个涨停、演变成涨停潮，'
        '就是有资金合力的题材（上表「热点题材榜」）。</li>'
        '<li><b>定龙头</b>：题材爆发后机会集中在涨势最猛、连板最高的龙头（上表「龙头梯队」，'
        '最高板 = 空间龙头）。前 1~2 个板难辨强弱，通常 3~6 板「大浪淘沙」后才见真龙。</li>'
        '<li><b>盯异动</b>：连板到一定阶段，先手获利盘下车 → 炸板/断板（上表「异动监控」）；'
        '此时若有资金承接 = 弱转强狙击点，若承接不住 = 分歧退潮。</li>'
        '<li><b>抓补涨</b>：龙头高位后，资金会找同题材低位股 —— 首板跟风、接力龙头、'
        '未板补涨（上表「补涨候选」）。</li>'
        '</ol>'
        '<div class="case">'
        '<b>案例 · AI短剧/漫剧（2026-10~11）：</b>10-14 传媒/游戏批量涨停→题材爆发；'
        '新经典、慈文传媒走出 4 连板，11-05 浙文影业一字 4 连板（约 78 万手封单）+ 引力传媒 4天3板为龙头；'
        '中文在线、捷成股份（20CM）、龙版传媒、上海电影、奥飞娱乐等为跟风补涨。'
        '（来源：新浪财经/证券时报 2026-10-15；腾讯自选股/21财经 2026-11-05）'
        '</div>'
        '<div class="case">'
        '<b>案例 · 创新药（2025-05~07）：</b>三生国健（5-19 启动、4 连板 20CM）→ 舒泰神（5-21 启动、主升约 4 倍）'
        '为首发龙头；随后昂利康（6 月 3 连板）、常山药业（累计 +147.69%）、广生堂（7 月 4 连板 20CM）、'
        '塞力医疗（4 连板、周 +51.55%）、联环药业为「接力龙头」——龙头接力即补涨的主线形态。'
        '（来源：东方财富财富号 2025-07-16；中新经纬 2025-06-10；新华财经 2025-07-05）'
        '</div>'
        '</div>')

    cap = (f'<div class="cap">数据日 {_esc(as_of)} · 来源：东方财富涨停板池/炸板池/跌停池/概念板块/行业成分。'
           'A 股交易时段（09:30-11:30 / 13:00-15:00）浏览器每分钟直连刷新，'
           '盘前盘后显示最近一次跑批快照。'
           '本板块为短线情绪观察，不构成投资建议，打板/追高为高风险行为，务必自行核验后决策。</div>')

    return ('<div class="zl chart" id="zl-root">'
            '<div class="mhead">'
            '<div class="t">超短线擒龙</div>'
            '<div class="sub">热点题材 → 龙头 → 异动 → 补涨　·　数据日 <b id="zl-date">{}</b>　·　'
            '涨停 <b id="zl-zt">{}</b> / 炸板 <b id="zl-zb">{}</b> / 最高 <b id="zl-maxlbc">{} 连板</b>'
            ' <span class="zl-at" id="zl-at"></span></div></div>'
            '<div id="zl-dyn">'
            '{}'  # stats
            '{}'  # picks (按题材分组龙头卡)
            '{}'  # tags
            '{}'  # themes
            '<div class="zl-grid">{}{}</div>'  # dragon + zhaban
            '{}'  # catchup
            '</div>'
            '{}'  # method
            '{}'  # cap
            '</div>').format(
        _esc(as_of), mkt.get("zt", 0), mkt.get("zb", 0), mkt.get("max_lbc", 0),
        stats, picks_html, tags, themes_html, dragon_html, zb_html, cu_html, method, cap)


# 每个区间对应什么情况，一句话。措辞只描述"情绪处在什么状态、历史上多出现在哪"，
# 不写买卖建议 —— 情绪指数只能说明"大家怎么想"，不能说明"接下来怎么走"。
MOOD_ZONE_TEXT = {
    0: "恐慌性抛售、避险情绪拉满。长期看常是布局区，但短期可能继续跌 —— 便宜还能更便宜。",
    25: "多数人观望，情绪偏谨慎。通常还没到最悲观的时点。",
    45: "多空接近平衡，情绪本身不构成信号。",
    56: "追高的人变多，最容易在「再涨一点就加仓」的预期里买在高位。",
    76: "几乎没人相信会跌，历史上多出现在阶段性顶部附近。",
}


def _mood_html(mood):
    """美股市场情绪（CNN 恐惧与贪婪）。纯展示，不参与任何标的的打分。"""
    if not mood:
        return ""
    zones = mood.get("zones") or []
    if not zones:
        return ""

    sc = float(mood.get("score") or 0)
    col = mood.get("color") or "#8a8d96"
    cur_lo = (mood.get("zone") or [0, 0])[0]

    # 色条：每段宽度 = 该区间包含的整数分数个数（0-24 是 25 个，45-55 是 11 个…），
    # 这样指针位置 score/101 与分段边界严丝合缝，不会出现"指针在恐惧、标签却写极度恐惧"。
    # 段之间不留 gap：刻度是按容器宽度百分比绝对定位的，留 gap 会让标签和实际边界错开几像素。
    segs = "".join(f'<i style="flex:{hi - lo + 1};background:{c}"></i>'
                   for lo, hi, _cn, c in zones)
    pos = max(0.0, min(100.0, sc)) / 101.0 * 100.0

    # 刻度必须按累计宽度定位，不能用 space-between 均分：
    # 均分会让 "25" 落在 20% 处，而它真实的边界在 24.75%，读图会以为 25 分还在极度恐惧区。
    acc, marks = 0, [(0.0, "0")]
    for lo, hi, _cn, _c in zones:
        acc += hi - lo + 1
        marks.append((acc / 101.0 * 100.0, str(hi + 1)))
    marks[-1] = (100.0, "100")      # 最后一段的右边界是 101 格，标签仍写 100
    ticks = "".join(f'<span style="left:{p:.2f}%">{t}</span>' for p, t in marks)

    rows = []
    for lo, hi, cn, c in zones:
        cls = ' class="on"' if lo == cur_lo else ""
        rows.append(f'<li{cls} data-lo="{lo}" style="--mc:{c}"><b>{lo}-{hi} {cn}</b>'
                    f'<em>{_esc(MOOD_ZONE_TEXT.get(lo, ""))}</em></li>')

    def _v(k):
        v = mood.get(k)
        return "—" if v is None else f"{v:.1f}"

    parts = mood.get("parts") or []
    drive = ""
    if parts:
        weak = min(parts, key=lambda p: p["score"])
        strong = max(parts, key=lambda p: p["score"])
        drive = (f'<div class="drive">往下拉最多：<b>{_esc(weak["name"])} {weak["score"]:.1f}</b>'
                 f'　·　最不悲观：<b>{_esc(strong["name"])} {strong["score"]:.1f}</b></div>')

    return f"""<div class="mood">
  <div class="ml">
    <div class="k">美股市场情绪<i class="fqmini">不参与打分</i></div>
    <div class="src">CNN Fear &amp; Greed · {_esc(mood.get('date') or '')} 数据</div>
    <div class="sc"><b id="mood-sc" style="color:{col}">{sc:.1f}</b><small>/100</small></div>
    <div class="lb" id="mood-lb" style="color:{col}">{_esc(mood.get('label') or '')}</div>
    <div class="delta" id="mood-delta">昨收 {_v('prev_close')} · 一周前 {_v('prev_week')}<br>
      一月前 {_v('prev_month')} · 一年前 {_v('prev_year')}</div>
    <div class="at" id="mood-at">每 60 秒直连 CNN 检查</div>
  </div>
  <div class="mr">
    <div class="gauge">
      <div class="gb">{segs}</div>
      <div class="gp" id="mood-pin" style="left:{pos:.2f}%"><span>{sc:.0f}</span></div>
      <div class="gt">{ticks}</div>
    </div>
    <ul class="zl" id="mood-zl">{''.join(rows)}</ul>
    {drive}
    <div class="note"><b>CNN 这个指数每天只更新一次</b>（美东收盘后）。这里每分钟检查一次，
      是为了它一更新页面就能反映，而不是干等下一批跑批。</div>
  </div>
</div>"""


def _labs_html(labs):
    """两张「长期锚」卡片 + 一张二十二年双线图。数据缺失时整块不渲染。"""
    if not labs:
        return "", "", ""
    da, cy, el = labs.get("div_anchor"), labs.get("cyb_ratio"), labs.get("equity_long")

    a = ""
    if da:
        s = da["series"]
        n = len(s)
        L = [
            {"pts": [(i, r[1]) for i, r in enumerate(s)], "color": "#111827", "width": 2.0},
            {"pts": [(i, r[2]) for i, r in enumerate(s)], "color": "#a8752a", "width": 2.3},
            {"pts": [(i, r[3]) for i, r in enumerate(s)], "color": "#2f6fb0", "width": 2.3},
        ]
        xl = [(0, s[0][0]), (n // 2, s[n // 2][0]), (n - 1, s[-1][0])]
        a += f"""<div class="lab">
  <div class="t">中证红利 · 月线锚</div>
  <div class="sub">40 月均线当估值中枢、90 月均线当深度低估参考点 —— 民间经验规则，非学术结论，这里只量「现在离这两条线多远」</div>
  <div class="big">{_num(da['close'])}<small>{da['month']} 收盘 · 点位</small></div>
  <div class="kv">
    <div class="c"><div class="k">vs 40 月均线 {_num(da['ma40'])}</div><div class="v">{_dev_html(da['dev40'], da['dev40_pct'])}</div></div>
    <div class="c"><div class="k">vs 90 月均线 {_num(da['ma90'])}</div><div class="v">{_dev_html(da['dev90'], da['dev90_pct'])}</div></div>
  </div>
  {_svg(L, xlabels=xl)}
  <div class="cap">月线 {da['months']} 期（2005-01 起）· <span style="color:#111827">黑</span>=月收盘　<span style="color:#a8752a">金</span>=MA40　<span style="color:#2f6fb0">蓝</span>=MA90</div>
</div>"""

    if cy:
        s = cy["series"]
        n = len(s)
        L = [{"pts": [(i, r[1]) for i, r in enumerate(s)], "color": "#a8752a", "width": 2.6}]
        refs = [(f"参考 {cy['ref']}", cy["ref"], "#b4512f")]
        xl = [(0, s[0][0]), (n // 2, s[n // 2][0]), (n - 1, s[-1][0])]
        gap = (cy["ratio"] / cy["ref"] - 1) * 100 if cy["ref"] else None
        gap_html = (f'<i class="{"up" if gap > 0 else "dn"}">{gap:+.1f}%</i>'
                    if gap is not None else "—")
        a += f"""<div class="lab">
  <div class="t">创业板指 ÷ 中证红利</div>
  <div class="sub">「直接指数相除」。比值越低，创业板相对红利越便宜；{cy['ref']} 是截图里提到的观察点</div>
  <div class="big">{cy['ratio']:.4f}<small>{cy['as_of']} · 历史分位 {_num(cy['pct'], 1)}%</small></div>
  <div class="kv">
    <div class="c"><div class="k">距 {cy['ref']} 参考点</div><div class="v">{gap_html}</div></div>
    <div class="c"><div class="k">区间（{cy['from']} 起，{cy['n']} 个交易日）</div><div class="v">{cy['min']:.4f} – {cy['max']:.4f}</div></div>
  </div>
  {_svg(L, refs=refs, xlabels=xl)}
  <div class="cap">历史低点 {cy['min']:.4f}（{cy['min_d']}）、高点 {cy['max']:.4f}（{cy['max_d']}）· 创业板指仅回溯到 {cy['from']}，故分位是近 12 年口径</div>
</div>"""

    b = ""
    if el and el.get("win"):
        wins = el["win"]
        order = [k for k in ("1y", "5y", "10y", "all") if k in wins]
        names = {"1y": "近 1 年", "5y": "近 5 年", "10y": "近 10 年"}
        try:
            _y0 = int(el["from"][:4])
            _y1 = int(el["to"][:4])
            all_lab = f"全部 {_y1 - _y0} 年"
        except Exception:  # noqa: BLE001
            all_lab = "全部"
        names["all"] = all_lab

        btns, panes = [], []
        for k in order:
            w = wins[k]
            pw = w["pts"]
            pn = w.get("pts_n") or pw
            on = (k == "all")

            def _layers(pts):
                return [
                    {"pts": [(j, r[2]) for j, r in enumerate(pts)], "color": "#111827", "width": 2.2},
                    {"pts": [(j, r[1]) for j, r in enumerate(pts)], "color": "#2f6fb0", "width": 2.2},
                ]

            wide = _svg(_layers(pw), w=1060, h=336, log=True,
                        pad=(54, 58, 16, 26), xlabels=_xlabels(pw, maxn=12),
                        fs=10, ends=True)
            # 窄屏没地方把末值标在线外，且右上角年化那块已经写了两个现值，就不标了
            narrow = _svg(_layers(pn), w=430, h=330, log=True,
                          pad=(44, 8, 14, 24), xlabels=_xlabels(pn, maxn=5),
                          fs=11)
            cls = ' class="on"' if on else ""
            btns.append(f'<button type="button" data-k="{k}"{cls}>{names[k]}</button>')
            panes.append(f'<div class="sw" data-k="{k}"{"" if on else " hidden"}>'
                         f'<div class="v-w">{wide}</div>'
                         f'<div class="v-n">{narrow}</div></div>')

        # 三个年化数字：画线口径（黑线不含分红、蓝线含分红）在前，同口径对比在后
        tr = el.get("cagr_market_tr")
        same = ""
        if tr is not None:
            same = (f'<div>同口径全收益：全市场 <b style="color:#111827">{_num(tr, 2)}%</b>'
                    f' · 沪深300 <b style="color:#2f6fb0">{_num(el["cagr300"], 2)}%</b></div>')
        b = f"""<div class="chart eqw" id="eqw">
  <div class="eqhead">
    <div>
      <div class="t">二十二年，两条线</div>
      <div class="sub">
        <span class="eqleg"><i style="background:#111827"></i>全市场 · 中证全指 <b>000985</b>（价格口径）</span>
        <span class="eqleg"><i style="background:#2f6fb0"></i>沪深300 <b>H00300</b>（全收益，含分红）</span>
        <div style="margin-top:3px">纵轴对数刻度 · 共 {el['days']} 个交易日（{el['from']} → {el['to']}）</div>
      </div>
    </div>
    <div class="eqnums">
      <div class="r">年化 · 画线口径</div>
      <div>全市场 <b style="color:#111827">{_num(el['cagr_market'], 2)}%</b>（{_num(el['market'], 0)} 点）</div>
      <div>沪深300 <b style="color:#2f6fb0">{_num(el['cagr300'], 2)}%</b>（{_num(el['h300'], 0)} 点）</div>
      {same}
    </div>
  </div>
  <div class="chartbar"><div class="btns">{''.join(btns)}</div>
    <div class="delta"><span class="lb">日频数据</span>每个点一个交易日，按窗口抽稀</div></div>
  {''.join(panes)}
  <div class="cap">左轴对数刻度（1 · 2 · 3 · 5 · 7 优选，等距离散）。黑线原图是<b>万得全A 800707.WI</b>，
    属 Wind 商业数据、公开接口取不到 → 改用中证全指 <code>000985</code> 价格指数近似（同为价格口径、基点 1000、覆盖全 A 股）；
    蓝线照原样为沪深300全收益 H00300。一条不含分红、一条含分红，所以只能比形态和斜率，
    比收益高低请看右上的「同口径全收益」。</div>
</div>"""
    return a, b, ""


def _signals_html(sg):
    """阈值提示条。tx 由 src/signals.py 自己拼（含 <b>），此处不再转义；
    其余字段一律 _esc，避免以后有人往 signals 里塞外部数据时出现注入。"""
    items = (sg or {}).get("items") or []
    if not items:
        return ""
    rows = []
    for s in items:
        lv = _esc(s.get("lv") or "mid")
        num = s.get("num")
        num_html = f"<span class='num'>{_esc(num)}</span>" if num else ""
        rows.append(
            f"<div class='sig {lv}'><span class='tag'>{_esc(s.get('tag', ''))}</span>"
            f"<div class='tx'>{s.get('tx', '')}</div>{num_html}</div>")
    rule = sg.get("rules") or ""
    tail = (f"<div class='sigrule'>阈值口径：{_esc(rule)}　·　"
            "提示只描述「现在处在哪个位置」，不构成买卖指令，也不改变上面的倍数</div>")
    return f"<div class='sigs'>{''.join(rows)}</div>{tail}"


def _js_payload(payload):
    """内联给 JS 的那份数据：去掉 labs 里只给服务端画 SVG 用的大数组。

    前端一行都不读 labs（图是服务端画好的），但 equity_long.win 里有两千多个
    日频点，原样内联等于每次打开都白下载几十 KB。数字类字段保留，删数组。
    """
    p = dict(payload)
    latest = dict(p.get("latest") or {})
    labs = dict(latest.get("labs") or {})
    for k in ("div_anchor", "cyb_ratio", "equity_long"):
        if isinstance(labs.get(k), dict):
            blk = dict(labs[k])
            blk.pop("series", None)
            if isinstance(blk.get("win"), dict):
                blk["win"] = {kk: {x: y for x, y in vv.items() if not x.startswith("pts")}
                              for kk, vv in blk["win"].items()}
            labs[k] = blk
    if labs:
        latest["labs"] = labs
    # 情绪指数的 251 个历史点只给服务端判断用，前端一行都不读（图是服务端画的），
    # 内联进去等于每次打开白下载 5KB
    if isinstance(latest.get("mood"), dict):
        m = dict(latest["mood"])
        m.pop("history", None)
        latest["mood"] = m
    # 指数技术位：K 线 600+ 根只给服务端画 SVG 用，前端一行都不读
    # （图是服务端画好的）。前端只读各指数 fib 7 条线 + 收盘价，用来每分钟重算压力/支撑距离。
    if isinstance(latest.get("sz_kline"), list):
        skl = []
        for sk in latest["sz_kline"]:
            if isinstance(sk, dict):
                sk = dict(sk)
                sk.pop("klines", None)
                skl.append(sk)
        latest["sz_kline"] = skl
    # 超短线擒龙：整段服务端渲染成 HTML，前端一行都不读（涨停板池是日频数据，
    # 不需要前端实时重算），内联进去只是白下载几 KB 的股票列表。
    latest.pop("zhulong", None)
    p["latest"] = latest
    return p


def render(payload):
    latest = payload["latest"]
    hist = payload["history"]
    # JSON 内联：转义 </script> 防止提前闭合
    data_js = json.dumps(_js_payload(payload), ensure_ascii=False).replace("</", "<\\/")

    # 结论摘要（服务端先算好，避免 JS 失效时页面空白）
    rows = []
    for a in latest["assets"]:
        ex = a.get("execution") or {}
        mult = "—" if a["advisory_only"] else f"{a['multiplier']:.1f}×"
        amt = "—" if a["advisory_only"] else f"{a['suggest_amount']:,.0f} 元"
        rows.append(
            "<tr>"
            f"<td style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1);color:#14161b'>{_esc(a['name'])}</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1)'>{a['score']:.1f}</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1);color:var(--dim2)'>"
            f"{(a.get('band_pos') or 50):.0f}%</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1);color:var(--gold-l)'>"
            f"<b style='font-weight:550'>{mult}</b></td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1)'>"
            f"{amt}</td>"
            f"<td class='mono' style='padding:9px 10px;border-bottom:1px solid rgba(20,22,27,.1);color:var(--dim)'>"
            f"{_esc(ex.get('fund_code') or '—')}</td>"
            "</tr>")
    summary = ("<div class='tscroll'><table style='width:100%;border-collapse:collapse;font-size:12.5px'>"
               "<thead><tr style='color:var(--dim3);font-size:9.5px;text-align:left;"
               "letter-spacing:.16em;text-transform:uppercase'>"
               "<th style='padding:0 10px 9px;font-weight:400'>标的</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>分数</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>档内</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>倍数</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>建议金额</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>落地基金</th>"
               "</tr></thead><tbody style='color:var(--txt)'>" + "".join(rows) +
               "</tbody></table></div>"
               "<div class='swipehint'>← 左右滑动看倍数 / 建议金额 / 落地基金 →</div>")

    # 观察型模块（不参与打分）：数据缺失时整段不输出，不留空壳
    month_sec = _month_html(latest)
    mood_sec = _mood_html(latest.get("mood") or {})
    labs_a, labs_b, _ = _labs_html(latest.get("labs") or {})
    sig_sec = _signals_html(payload.get("signals") or {})
    szk_sec = _sz_kline_sections(latest.get("sz_kline"))
    zl_sec = _zhulong_html(latest.get("zhulong"))
    labs_sec = ""
    if labs_a:
        labs_sec += ('<h2>长期锚 <small>不参与打分 · 只量「现在离长期参考点多远」</small>'
                     '<em class="fq snap">随跑批刷新</em></h2>\n'
                     f'<div class="labs">{labs_a}</div>\n')
    if labs_b:
        labs_sec += ('<h2>二十二年 <small>日频 · 对数轴 · 两条线口径不同</small>'
                     '<em class="fq snap">随跑批刷新</em></h2>\n'
                     f'{labs_b}\n')

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#f7f5f1">
<meta name="color-scheme" content="light">
<title>定投台 · {_esc(latest['trade_date'])}</title>
<script>
/* 版本自检（渲染前执行）：收藏的稳定入口不带 query，GitHub Pages 的 CDN 会缓存它最多
   10 分钟、手机浏览器（微信/QQ 内核）还可能缓存更久，导致旧主题/旧数据迟迟不换新。
   这里在画任何内容前自检一次：本地记录的构建号落后于当前构建，就跳转到带版本号的 URL
   （唯一 URL → CDN 回源），一次拿到最新版。localStorage 记档，只跳一次，不会「反复刷新」。 */
(function(){{
  try{{
    if(location.protocol.indexOf('http') !== 0) return;   // file:// 本地预览跳过
    if(location.search) return;                            // 已带 ?v=，不重复跳
    var V = "{latest.get('generated_at_ts', '')}";
    if(V && localStorage.getItem('__dca_build__') !== V){{
      localStorage.setItem('__dca_build__', V);
      location.replace(location.pathname + '?v=' + V);
    }}
  }}catch(e){{}}
}})();
</script>
<style>{CSS}</style></head>
<body><div class="wrap">

<div class="hd">
  <div class="brand"><h1>定投台</h1><span class="en">DCA Dashboard</span></div>
  <div class="meta" id="meta"></div>
</div>

<div class="newbar" id="newbar" hidden>
  <span>后台已更新到 <b id="newat">—</b> 的版本，你正在看的是 <b id="curat">—</b> 的快照</span>
  <button type="button" onclick="loadNew()">加载新数据</button>
</div>

<div class="hero" id="hero"></div>

<div class="dirbar">
  <span class="tagk">分数怎么读</span>
  <span><b>分数越高 → 越便宜 → 建议买得越多</b></span>
  <span class="sep">|</span>
  <span class="q">50 分 = 1.0×　·　≥ 56 分加仓　·　&lt; 40 分减仓　·　分数是「贵不贵」，不是价格涨跌</span>
</div>

<div class="live" id="live"></div>
{mood_sec}
{sig_sec}
<div class="macro" id="macro"></div>

<h2>标的评分 <small>卡片内的分数与点位一律按最近收盘算</small><em class="fq snap">每交易日 6 次</em></h2>
<div class="grid" id="grid"></div>

<h2>本期结论 <small>分数越高越该买 · 50 分 = 1.0 倍</small><em class="fq snap">每交易日 6 次</em></h2>
<div class="notes">{summary}</div>

<h2>近一月涨跌 <small>价格口径 · 与分数无关 · 近 7 天单独标出</small><em class="fq snap">随跑批刷新</em></h2>
{month_sec or '<div class="notes"><div class="cap">该模块数据不足，本期不画</div></div>'}

<h2>指数技术位 <small>斐波那契回调 · 压力/支撑 · 不参与打分</small><em class="fq rt">当前价每分钟实时</em></h2>
{szk_sec or '<div class="notes"><div class="cap">该模块数据不足，本期不画</div></div>'}

<h2>超短线擒龙 <small>按题材分组 · 领涨/补涨龙头（可买标红） · 热点题材 · 龙头梯队 · 异动 · 不参与打分</small><em class="fq rt">盘中每分钟实时刷新</em></h2>
{zl_sec or '<div class="notes"><div class="cap">该模块数据不足，本期不画</div></div>'}

<h2>分数历史 <small>分数越高越便宜 → 买得越多 · 50 分 = 1.0×</small><em class="fq snap">每交易日 6 次</em></h2>
<div class="charthint">
  <span class="up"><i></i>↑ 分数越高 = 越便宜 = 建议买得越多</span>
  <span class="dn"><i></i>↓ 分数越低 = 越贵 = 建议买得越少</span>
  <span>金色虚线 = 50 分 = 1.0× 基准</span>
</div>
<div class="chartbar" id="chartbar"></div>
<div class="chart" id="chart"></div>

{labs_sec}
<h2>口径与数据来源</h2>
<div class="notes">
  <ul>
    <li><b>更新频率分三层，不是所有数字都实时。</b>
        ① <b>实时行情条</b>（页面顶部那一排）= 浏览器每 60 秒直连腾讯行情，只有「价格 + 当日涨跌幅」，
        标着绿色「实时」；<br>
        ② <b>分数 / 倍数 / 分数历史曲线 / 近一月涨跌 / 长期锚 / 二十二年</b> = 跑批时整体重算，
        每交易日 6 次（北京 08:07 / 10:07 / 11:17 / 13:37 / 14:47 / 15:17），
        区块标题右侧标着「每交易日 6 次」或「随跑批刷新」；<br>
        ③ <b>宏观利率那排</b> = 日频数据，跟着跑批刷新，标着「日频」。<br>
        所以：行情条每分钟在动，分数一天最多变 6 次。<b>分数不会每分钟变，也不该每分钟变</b>——
        它的输入（PE、股息率、国债利率）本身就是日频/周频的，日内只有价格在动，
        每分钟重算只会让同一个分数在几分钱的价格波动里来回抖。</li>
    <li><b>分数方向</b>：0–100，<b>越高表示当下越便宜/越恐慌、越该多买</b>。50 分 = 1.0 倍基准。</li>
    <li><b>带宽</b>：≥82→2.0×　68–82→1.5×　56–68→1.2×　<b>40–56→1.0×</b>　28–40→0.8×　14–28→0.5×　&lt;14→0.3×。
        中性带 16 分宽，避免分数抖 1 分就换档。</li>
    <li><b>档内位置</b>：同一倍数档内部的相对位置，越靠右越接近上调一档。同档多个标的用它排先后。</li>
    <li><b>评分一律用指数本身，不用基金净值。</b>基金净值有三重失真：分红/折算造成单日跳降、QDII 的 T+1/T+2 披露导致日期错位、管理费持续侵蚀。</li>
    <li><b>申购状态不参与打分、不改倍数。</b>同一份行情不该因为渠道临时限购给出不同倍率；限购只影响「钱能不能落到那只基金」。</li>
  </ul>
  <div class="warnbox">
    <b>已知口径缺口（不掩盖）</b><br>
    · 纳斯达克综合指数自身 PE 不可得 → 用纳指100(NDX) 估值代理<br>
    · <b>MSCI 全球医疗保健指数的 PE 历史不可得</b>（官方基本面接口需订阅，实测 404；蛋卷未覆盖）→ 估值改用「医疗/MSCI World 比价分位」+「距 10 年对数趋势偏离」两个真实代理。官方快照 2026-08-31：PE 22.44、PB 4.85<br>
    · 中证红利真实股息率历史序列不可得 → 用 PE 分位反向代理<br>
    · A 股 10Y 国债未接入（中债接口需鉴权）→ 红利宏观用「相对沪深300 强弱」+「沪深300 PE 分位」替代<br>
    · 黄金价格分位为名义口径，未做通胀调整<br>
    · <b>「长期锚」三块不参与打分</b>：40/90 月均线、创红比 0.3 都来自民间经验规则（非学术结论），页面只量「现在离参考点多远」<br>
    · 万得全A(800707.WI) 属 Wind 商业数据、公开接口取不到 → 「全市场」一条改用中证全指全收益 H00985 替代（同口径、同基点）<br>
    · 创业板指公开接口只回溯到 2014-06 → 创红比分位是「近 12 年」口径，不是全历史
  </div>
  <ul>
    <li><b>数据来源</b>：MSCI 官方指数接口（106801 / 990100）· 新浪财经 US_MinKService（.IXIC/.NDX/.INX）·
        东方财富 push2his（GC00Y/000922/000300/UDI/USDCNH）· 美国财政部 official CSV（TIPS 与名义收益率）·
        蛋卷基金 index_eva（PE 周频序列 + PB 分位）· 天天基金（净值与申购状态）·
        中证指数官网 index-perf（000922 / H00300 沪深300全收益 / H00985 中证全指全收益）·
        新浪 sz399006（创业板指，3000 条上限）·
        东方财富 push2ex 涨停板池 / 炸板池 / 跌停池 + 概念板块涨幅榜 + 行业成分（「超短线擒龙」板块，日频）</li>
    <li><b>跟踪误差实测</b>（纳指100 六只候选，QDII 净值按 T+1 对齐后年化）：
        广发 000055 = 0.83%　华安 040046 = 1.00%　大成 000834 = 1.03%　南方 016452 = 1.42%　天弘 018043 = 1.46%　国泰 160213 = 11.83%</li>
  </ul>
</div>

<div class="foot">
  本工具仅为个人定投纪律辅助。所有分数与倍数由公开数据按固定规则机械计算，同一份数据必得同一结果，可复现、可复盘。<br>
  不构成任何投资建议。数据可能存在延迟或错误，请自行核验后决策。历史分位不代表未来。<br>
  最后生成 {_esc(latest['generated_at'])} · 快照期数 {len(hist)}
</div>

</div>
<script>window.__DATA__ = {data_js};</script>
<script>{JS}</script>
</body></html>"""
