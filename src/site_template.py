# -*- coding: utf-8 -*-
"""生成 docs/index.html。

纯手写 HTML/CSS/JS + 内联 SVG，不引 CDN：
GitHub Pages 是静态托管，引外部图表库一旦被墙整页白屏，手绘 SVG 最稳。
数据由 Python 侧直接内联，前端零 fetch。

视觉：纯黑底 + 香槟金点缀，细发丝描边，无圆角堆叠，走「高级感」路线。
"""
import json

# ---------------------------------------------------------------- 样式

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f7f5f1; --bg-2:#f2f0eb;
  --card-a:#ffffff; --card-b:#fdfcf9;
  --line:rgba(20,22,27,.11); --line-2:rgba(20,22,27,.2);
  --txt:#14161b; --dim:#3d4048; --dim2:#5d6069; --dim3:#878a93;
  --gold:#9c782f; --gold-l:#6f5520; --gold-d:#c6a860;
  --ink:#66727e; --ok:#2f7d54; --hot:#b4452e;
  --r:14px;
}
html{background:var(--bg);-webkit-text-size-adjust:100%}
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
  display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}
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
@media (max-width:760px){
  .mchart .v-w{display:none} .mchart .v-n{display:block}
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
  /* 二十二年四个窗口按钮要在一行里排开，手机上把内边距收紧 */
  .eqw .chartbar button{font-size:11.5px;padding:5px 9px;letter-spacing:.02em}
  .eqw .chartbar .delta{margin-left:0;font-size:10px}
  .charthint{font-size:11.5px;gap:12px}
}
"""

JS = """
const P = window.__DATA__;
function fmtPx(v){ if(v==null) return '—';
  return Math.abs(v)>=100 ? v.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})
                          : v.toFixed(4); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
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
      '<b>' + (L.trade_date || '') + '</b> · ' + (L.generated_at || '').slice(11, 16) + ' 生成' +
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
  const W = narrow ? 430 : 1100, H = narrow ? 340 : 330;
  const PL = narrow ? 26 : 40, PR = narrow ? 10 : 16, PT = narrow ? 16 : 22,
        PB = narrow ? 26 : 30;
  // 五条线要能在手机上分开：金 / 近黑 / 靛蓝 / 墨绿 / 砖红，明度与色相都拉开
  const colors = ['#a8752a','#111827','#2f6fb0','#2f7d5e','#b4512f'];
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
      '<stop offset="0%" stop-color="'+colors[ci%colors.length]+'" stop-opacity=".7"/>'+
      '<stop offset="55%" stop-color="'+colors[ci%colors.length]+'" stop-opacity=".96"/>'+
      '<stop offset="100%" stop-color="'+colors[ci%colors.length]+'" stop-opacity="1"/></linearGradient>';
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
      '" r="2.8" fill="'+colors[ci%colors.length]+'"/>';
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
    // 末值放图例里而不是贴在曲线右端：四条线收在 35–52 区间，右端标数值必然叠在一起
    leg += '<span style="display:inline-flex;align-items:center;gap:7px">'+
      '<i style="width:12px;height:2px;border-radius:2px;background:'+colors[ci%colors.length]+
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
      bh += '<span class="dd"><i style="background:'+colors[ci%colors.length]+'"></i>'+
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
  {c:'sh000300',nm:'沪深300'}
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
      // 从后往前找时间戳：A 股是 14 位紧凑时间(20261023120549)，美股带横线。
      // 不能从前往后找 —— 成交量字段(37926310)也是 8 位数字，会被误判成日期。
      let ti=-1;
      for(let i=p.length-1;i>=3;i--){
        if(/^[0-9]{14}$/.test(p[i])||/^[0-9]{4}-[0-9]{2}-[0-9]{2}/.test(p[i])){ ti=i; break; }
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
  // MSCI 全球医疗没有公开实时源：显示最近收盘价，明确标「收盘」，不冒充实时
  const h=(P.latest.assets||[]).filter(function(a){ return /医疗/.test(a.name); })[0];
  if(h&&h.price!=null){
    const md=String(h.price_date||'').slice(5);
    cells.push('<div class="cell"><div class="nm">MSCI 全球医疗<i>收盘'+(md?' '+md:'')+'</i></div>'+
      '<div class="px">'+fmtPx(h.price)+'</div></div>');
  }
  if(!cells.length){ box.style.display='none'; return; }
  // 「本次 HH:MM:SS」是刻意加的：页面挂在后台或接口静默失败时，这一行会停住不动，
  // 用户一眼就能看出「是没刷新」还是「刷新了但价格没变」。
  const nw = new Date();
  const at = ('0'+nw.getHours()).slice(-2)+':'+('0'+nw.getMinutes()).slice(-2)+
             ':'+('0'+nw.getSeconds()).slice(-2);
  const perDay = (P.schedule && P.schedule.tods) ? P.schedule.tods.length : 4;
  box.innerHTML = cells.join('')+
    '<div class="stamp"><span>行情时间 <b>'+(stamp?esc(stamp):'—')+
    '</b> · 浏览器直连腾讯行情，每 60 秒刷新（本次 '+at+'）</span>'+
    '<span><b>实时价只用来感受当下位置，不参与打分</b>；分数与倍数按已收盘数据算，每交易日 '+
    perDay+' 次</span></div>';
}
function loadLive(){
  const s=document.createElement('script');
  s.charset='gbk';
  s.src='https://qt.gtimg.cn/q='+LIVE.map(function(x){return x.c;}).join(',')+'&_='+Date.now();
  s.onload=function(){ renderLive(); };
  s.onerror=function(){ const b=document.getElementById('live'); if(b) b.style.display='none'; };
  document.head.appendChild(s);
  setTimeout(renderLive, 4000);   // 兜底：脚本静默失败时也试一次
}

/* 二十二年那张图的窗口切换（服务端已生成好几份 SVG，这里只切显示） */
function bindEqw(){
  const roots=document.querySelectorAll('.eqw');
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
// 每 60 秒拉一次实时价。页面在后台时跳过 —— 移动端浏览器会把后台定时器节流到几分钟一次，
// 与其那样半死不活地拉，不如不拉；切回前台时立刻补一次，不用干等下一个整分钟。
setInterval(function(){ if(!document.hidden) loadLive(); }, 60000);
document.addEventListener('visibilitychange', function(){
  if(!document.hidden) loadLive();
});

// 横竖屏切换 / 窗口缩放时重画分数图（窄屏和宽屏用不同画布尺寸）
let _rz = null;
window.addEventListener('resize', function(){
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

    PL, PR, PT, PB = 50, 54, 18, 26
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
    ends = sorted((Y(pts[-1][1]), pts[-1][1], col, X(pts[-1][0])) for _, _, col, pts in ser)
    gap = fs * 1.62
    fixed = []
    for y, lv, col, xx in ends:
        if fixed and y - fixed[-1][0] < gap:
            y = fixed[-1][0] + gap
        fixed.append((y, lv, col, xx))
    over = (fixed[-1][0] + fs * 0.35) - (h - PB + fs)
    if over > 0:                     # 推到底边外就整组上移
        fixed = [(y - over, lv, col, xx) for y, lv, col, xx in fixed]
    for y, lv, col, xx in fixed:
        o.append(f'<text x="{xx + 7:.1f}" y="{y + fs * 0.35:.1f}" fill="{col}" '
                 f'font-size="{fs + 1}" font-weight="600" text-anchor="start" '
                 'paint-order="stroke fill" stroke="#fff" stroke-width="3" '
                 f'stroke-linejoin="round">{lv:+.2f}%</text>')

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
    narrow = _month_svg(items, w=430, h=290, fs=11, maxx=3)
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
    labs_a, labs_b, _ = _labs_html(latest.get("labs") or {})
    sig_sec = _signals_html(payload.get("signals") or {})
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
<style>{CSS}</style></head>
<body><div class="wrap">

<div class="hd">
  <div class="brand"><h1>定投台</h1><span class="en">DCA Dashboard</span></div>
  <div class="meta" id="meta"></div>
</div>

<div class="hero" id="hero"></div>

<div class="dirbar">
  <span class="tagk">分数怎么读</span>
  <span><b>分数越高 → 越便宜 → 建议买得越多</b></span>
  <span class="sep">|</span>
  <span class="q">50 分 = 1.0×　·　≥ 56 分加仓　·　&lt; 40 分减仓　·　分数是「贵不贵」，不是价格涨跌</span>
</div>

<div class="live" id="live"></div>
{sig_sec}
<div class="macro" id="macro"></div>

<h2>标的评分 <small>卡片内的分数与点位一律按最近收盘算</small><em class="fq snap">每交易日 6 次</em></h2>
<div class="grid" id="grid"></div>

<h2>本期结论 <small>分数越高越该买 · 50 分 = 1.0 倍</small><em class="fq snap">每交易日 6 次</em></h2>
<div class="notes">{summary}</div>

<h2>近一月涨跌 <small>价格口径 · 与分数无关 · 近 7 天单独标出</small><em class="fq snap">随跑批刷新</em></h2>
{month_sec or '<div class="notes"><div class="cap">该模块数据不足，本期不画</div></div>'}

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
        新浪 sz399006（创业板指，3000 条上限）</li>
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
