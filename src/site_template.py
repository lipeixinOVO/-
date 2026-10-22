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
  --bg:#000000; --bg-2:#050506;
  --card-a:#0d0e11; --card-b:#08090b;
  --line:rgba(255,255,255,.075); --line-2:rgba(255,255,255,.14);
  --txt:#f3f3f5; --dim:#a0a0a9; --dim2:#6f7079; --dim3:#4c4d55;
  --gold:#d9b573; --gold-l:#f0d9a8; --gold-d:#8c6f3c;
  --ink:#7f8b96; --ok:#79c39a; --hot:#d9795f;
  --r:14px;
}
html{background:var(--bg);-webkit-text-size-adjust:100%}
body{
  background:
    radial-gradient(1100px 520px at 50% -220px, rgba(217,181,115,.075), transparent 62%),
    radial-gradient(760px 420px at 88% 8%, rgba(120,150,190,.045), transparent 60%),
    #000;
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
.hd h1{font-size:27px;font-weight:600;letter-spacing:.16em;color:#fff}
.hd .en{font-size:9.5px;letter-spacing:.34em;color:#a5844a;
  text-transform:uppercase;padding-bottom:4px}
.hd .meta{font-size:11.5px;color:var(--dim2);text-align:right;line-height:1.95;letter-spacing:.02em}
.hd .meta b{color:var(--dim);font-weight:500}
.hd .dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--gold);
  margin-right:6px;vertical-align:1px;box-shadow:0 0 8px rgba(217,181,115,.8)}

/* ---------- 结论条 ---------- */
.hero{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:var(--r);overflow:hidden;margin:26px 0 10px}
.hero>div{background:linear-gradient(180deg,var(--card-a),var(--card-b));padding:17px 20px 18px}
.hero .k{font-size:9.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--dim2)}
.hero .v{font-size:23px;font-weight:500;margin-top:7px;letter-spacing:-.01em;line-height:1.25}
.hero .v.pick{color:var(--gold-l)}
.hero .hint{font-size:11px;color:var(--dim2);margin-top:5px;letter-spacing:.02em}

/* ---------- 宏观条 ---------- */
.macro{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:var(--r);
  overflow:hidden;margin:22px 0 4px}
.macro div{background:#07080a;padding:12px 16px 13px}
.macro .k{font-size:9.5px;letter-spacing:.16em;color:#55565e;text-transform:uppercase}
.macro .v{font-size:16px;font-weight:500;margin-top:3px;color:#e9e9ec}
.macro .v small{font-size:10px;color:var(--dim2);font-weight:400;margin-left:2px}

/* ---------- 标的卡 ---------- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(346px,1fr));gap:14px;margin-top:18px}
.card{position:relative;background:linear-gradient(180deg,var(--card-a) 0%,var(--card-b) 100%);
  border:1px solid var(--line);border-radius:var(--r);padding:19px 20px 16px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 26px 50px -40px #000;
  transition:border-color .22s ease,box-shadow .22s ease,transform .22s ease}
.card:hover{border-color:rgba(217,181,115,.26);transform:translateY(-2px);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 32px 60px -38px #000,0 0 0 1px rgba(217,181,115,.05)}
.card.ref{opacity:.66}
.card.ref:hover{opacity:.86}
.card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.card .nm{font-size:14.5px;font-weight:550;line-height:1.4;letter-spacing:.01em;color:#fff}
.card .px{font-size:10.5px;color:var(--dim3);margin-top:4px;letter-spacing:.03em}
.card .tag{font-size:9px;padding:2.5px 7px;border-radius:3px;color:var(--dim2);
  border:1px solid var(--line-2);letter-spacing:.14em;text-transform:uppercase;white-space:nowrap}

.card .mid{display:flex;align-items:flex-end;gap:14px;margin:17px 0 15px}
.score{font-size:42px;font-weight:300;line-height:.92;letter-spacing:-.03em;
  background:linear-gradient(180deg,#fff,#b9b9c0);-webkit-background-clip:text;
  background-clip:text;-webkit-text-fill-color:transparent}
.score small{font-size:11px;color:var(--dim3);margin-left:4px;vertical-align:3px;
  -webkit-text-fill-color:var(--dim3);letter-spacing:.06em}
.mult{font-size:21px;font-weight:500;padding:5px 12px;border-radius:7px;line-height:1.25;
  white-space:nowrap;letter-spacing:.01em}
.mult.up{background:linear-gradient(180deg,rgba(240,217,168,.16),rgba(217,181,115,.07));
  color:var(--gold-l);border:1px solid rgba(217,181,115,.3)}
.mult.base{background:rgba(255,255,255,.04);color:#c2c2c9;border:1px solid var(--line-2)}
.mult.down{background:rgba(255,255,255,.02);color:var(--ink);border:1px solid var(--line)}
.lbl{font-size:10.5px;color:var(--dim2);margin-left:auto;text-align:right;line-height:1.6;
  letter-spacing:.02em}

/* 档内位置 */
.band{margin-bottom:15px}
.band .track{height:3px;background:#151619;border-radius:2px;position:relative;overflow:hidden}
.band .fill{height:100%;border-radius:2px;
  background:linear-gradient(90deg,var(--gold-d),var(--gold) 65%,var(--gold-l))}
.band .cap{display:flex;justify-content:space-between;font-size:9.5px;color:var(--dim3);
  margin-top:5px;letter-spacing:.1em;text-transform:uppercase}

/* 四维 */
.dims{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;margin-bottom:13px}
.dim{font-size:11px}
.dim .r{display:flex;justify-content:space-between;color:var(--dim2);margin-bottom:4px;letter-spacing:.03em}
.dim .r b{color:#dcdce1;font-weight:500}
.dim .t{height:2.5px;background:#151619;border-radius:2px;overflow:hidden}
.dim .f{height:100%;border-radius:2px;transition:width .3s ease}

/* 底部 */
.fund{font-size:10.5px;color:var(--dim2);padding-top:12px;border-top:1px solid var(--line);
  display:flex;justify-content:space-between;gap:8px;align-items:center;letter-spacing:.02em}
.fund .code{color:#d6d6dc;font-family:ui-monospace,monospace;letter-spacing:.04em}
.st{font-size:9.5px;padding:1.5px 6px;border-radius:3px;white-space:nowrap;letter-spacing:.05em}
.st.ok{background:rgba(121,195,154,.1);color:var(--ok)}
.st.lim{background:rgba(217,181,115,.11);color:var(--gold)}
.st.no{background:rgba(217,121,95,.1);color:var(--hot)}

/* ---------- 区块标题 ---------- */
h2{font-size:12px;font-weight:500;margin:44px 0 14px;padding-bottom:11px;
  border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:12px;
  letter-spacing:.2em;text-transform:uppercase;color:#e6e6ea}
h2 small{font-size:10.5px;color:var(--dim3);font-weight:400;letter-spacing:.06em;text-transform:none}

/* ---------- 图表 ---------- */
.chart{background:linear-gradient(180deg,var(--card-a),var(--card-b));border:1px solid var(--line);
  border-radius:var(--r);padding:20px 18px 16px}
.chart svg{width:100%;height:auto;display:block}

/* ---------- 文字块 ---------- */
.notes{background:linear-gradient(180deg,#0a0b0d,#07080a);border:1px solid var(--line);
  border-radius:var(--r);padding:20px 22px;font-size:12.5px;color:var(--dim);
  line-height:1.95;letter-spacing:.01em}
.notes b{color:#e2e2e7;font-weight:500}
.notes li{margin-left:16px;margin-bottom:4px}
.notes code{background:rgba(255,255,255,.05);padding:1px 5px;border-radius:3px;font-size:11px;
  font-family:ui-monospace,monospace;color:#c9c9d0}
.notes .warnbox{border-left:1px solid var(--gold-d);padding-left:14px;margin:14px 0;
  color:#a89a80;background:linear-gradient(90deg,rgba(217,181,115,.05),transparent 70%);
  padding-top:8px;padding-bottom:8px}

.foot{margin-top:48px;padding-top:20px;border-top:1px solid var(--line);
  font-size:10.5px;color:var(--dim3);line-height:1.9;letter-spacing:.04em}

@media(max-width:720px){
  .hero{grid-template-columns:1fr 1fr}
  .hero>div:first-child{grid-column:1/-1}
}
@media(max-width:560px){
  .wrap{padding:0 15px 64px}
  .grid{grid-template-columns:1fr}
  .score{font-size:36px}
  .mult{font-size:19px}
  .hd h1{font-size:21px;letter-spacing:.1em}
  .hd{padding-top:26px}
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
  if(sc>=65) return 'linear-gradient(90deg,#8c6f3c,#f0d9a8)';
  if(sc>=50) return 'linear-gradient(90deg,#6f6247,#d9b573)';
  if(sc>=35) return 'linear-gradient(90deg,#3f4450,#8a9aa8)';
  return 'linear-gradient(90deg,#3a3b40,#6a6b72)';
}
function render(){
  const L = P.latest;
  document.getElementById('meta').innerHTML =
    '<span class="dot"></span>数据日 <b>'+(L.trade_date||'')+'</b> · 生成 '+(L.generated_at||'').slice(11,16)+
    '<br>基准 <b>'+L.base_amount.toLocaleString('zh-CN')+' 元/月</b> · 历史 <b>'+
    P.history.length+'</b> 期';

  // 结论条：全部标的里分数最高的（含参考指数则标注）
  const ex_ = L.assets.filter(a=>!a.advisory_only);
  const sorted = ex_.slice().sort((a,b)=>b.score-a.score);
  const top = sorted[0], low = sorted[sorted.length-1];
  const upN = ex_.filter(a=>a.multiplier>1.02).length;
  document.getElementById('hero').innerHTML =
    '<div><div class="k">本期最该加仓</div><div class="v pick">'+esc(top.name)+
      '</div><div class="hint">'+top.score.toFixed(1)+' 分 · '+top.multiplier.toFixed(1)+
      '× · '+(top.suggest_amount?top.suggest_amount.toLocaleString('zh-CN')+' 元':'—')+'</div></div>'+
    '<div><div class="k">相对最贵</div><div class="v">'+esc(low.name)+
      '</div><div class="hint">'+low.score.toFixed(1)+' 分 · '+low.multiplier.toFixed(1)+'×</div></div>'+
    '<div><div class="k">上调档位</div><div class="v">'+upN+' / '+ex_.length+
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
    return '<div><div class="k">'+k+'</div><div class="v num">'+
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
      '<div class="px num">'+(a.kind==='commodity'?'':'点位 ')+fmtPx(a.price)+' · '+(a.price_date||'')+'</div></div>'+
      '<div class="tag">'+(a.advisory_only?'参考':'可执行')+'</div></div>'+
      '<div class="mid"><div class="score num">'+a.score.toFixed(1)+'<small>分</small></div>'+
      '<div class="mult '+multCls(a.multiplier)+' num">'+(a.advisory_only?'—':mult+'×')+'</div>'+
      '<div class="lbl">'+(a.advisory_only?'不执行':esc(a.label))+'<br>档内 '+bp.toFixed(0)+'%</div></div>'+
      '<div class="band"><div class="track"><div class="fill" style="width:'+Math.max(2,bp)+'%"></div></div>'+
      '<div class="cap"><span>本档下沿</span><span>越靠右越接近上调</span></div></div>'+
      '<div class="dims">'+dims+'</div>'+fund+'</div>';
  }).join('');

  renderChart();
}

function renderChart(){
  const S = P.series||{};
  const ids = (S.ids||[]).filter(function(id){ return id!=='IXIC'; });
  const box = document.getElementById('chart');
  const days = P.history.length;
  if(days < 2){
    box.innerHTML = '<div style="padding:28px;text-align:center;color:var(--dim3);font-size:12px;letter-spacing:.05em">'+
      '历史曲线需要至少 2 个交易日，当前第 <b style="color:var(--dim)">'+days+
      '</b> 天。每天跑批自动累积，250 期后形成完整一年曲线。</div>';
    return;
  }
  const W=1100, H=330, PL=40, PR=16, PT=22, PB=30;
  const all = [];
  ids.forEach(function(id){ (S.data[id]||[]).forEach(function(p){ all.push(p.s); }); });
  const mn = Math.max(0, Math.min.apply(null, all)-5);
  const mx = Math.min(100, Math.max.apply(null, all)+5);
  const n = days;
  const x = function(i){ return PL + (n<=1?0:(W-PL-PR)*i/(n-1)); };
  const y = function(v){ return PT + (H-PT-PB)*(1-(v-mn)/Math.max(1e-9,mx-mn)); };
  const colors = ['#f0d9a8','#d9b573','#9fb0c0','#7f8b96','#c98f6a'];

  let svg = '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet">';
  svg += '<defs>';
  ids.forEach(function(id,ci){
    svg += '<linearGradient id="g'+ci+'" x1="0" y1="0" x2="1" y2="0">'+
      '<stop offset="0%" stop-color="'+colors[ci%colors.length]+'" stop-opacity=".52"/>'+
      '<stop offset="55%" stop-color="'+colors[ci%colors.length]+'" stop-opacity=".92"/>'+
      '<stop offset="100%" stop-color="'+colors[ci%colors.length]+'" stop-opacity="1"/></linearGradient>';
  });
  svg += '</defs>';
  for(let k=0;k<=4;k++){
    const v = mn + (mx-mn)*k/4, yy = y(v);
    svg += '<line x1="'+PL+'" y1="'+yy+'" x2="'+(W-PR)+'" y2="'+yy+
      '" stroke="rgba(255,255,255,.055)" stroke-width="1"/>';
    svg += '<text x="'+(PL-9)+'" y="'+(yy+3.5)+'" fill="#5a5b63" font-size="10" text-anchor="end">'+
      v.toFixed(0)+'</text>';
  }
  if(50>mn && 50<mx){
    svg += '<line x1="'+PL+'" y1="'+y(50)+'" x2="'+(W-PR)+'" y2="'+y(50)+
      '" stroke="rgba(217,181,115,.4)" stroke-width="1" stroke-dasharray="3 5"/>';
    svg += '<text x="'+(W-PR)+'" y="'+(y(50)-7)+'" fill="#8a7448" font-size="9.5" '+
      'text-anchor="end" letter-spacing="1.5">1.0× BASELINE · 50</text>';
  }
  ids.forEach(function(id,ci){
    const pts = (S.data[id]||[]);
    if(!pts.length) return;
    const d = pts.map(function(p,i){
      return (i?'L':'M')+x(i).toFixed(1)+' '+y(p.s).toFixed(1); }).join(' ');
    svg += '<path d="'+d+'" fill="none" stroke="url(#g'+ci+')" stroke-width="2" '+
      'stroke-linejoin="round" stroke-linecap="round"/>';
    const last = pts[pts.length-1];
    svg += '<circle cx="'+x(pts.length-1).toFixed(1)+'" cy="'+y(last.s).toFixed(1)+
      '" r="2.6" fill="'+colors[ci%colors.length]+'"/>';
  });
  const hist = P.history;
  [0, Math.floor(n/2), n-1].forEach(function(i){
    const dd = (hist[i]||{}).trade_date||'';
    svg += '<text x="'+x(i).toFixed(1)+'" y="'+(H-8)+'" fill="#5a5b63" font-size="10" '+
      'letter-spacing=".5" text-anchor="'+(i===0?'start':(i===n-1?'end':'middle'))+'">'+dd+'</text>';
  });
  svg += '</svg>';

  let leg = '<div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:14px;font-size:10.5px;'+
    'color:var(--dim2);letter-spacing:.06em">';
  ids.forEach(function(id,ci){
    leg += '<span style="display:inline-flex;align-items:center;gap:7px">'+
      '<i style="width:12px;height:2px;border-radius:2px;background:'+colors[ci%colors.length]+
      ';display:inline-block"></i>'+esc((S.names||{})[id]||id)+'</span>';
  });
  leg += '</div>';
  box.innerHTML = svg + leg;
}
render();
"""


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def render(payload):
    latest = payload["latest"]
    hist = payload["history"]
    # JSON 内联：转义 </script> 防止提前闭合
    data_js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    # 结论摘要（服务端先算好，避免 JS 失效时页面空白）
    rows = []
    for a in latest["assets"]:
        ex = a.get("execution") or {}
        mult = "—" if a["advisory_only"] else f"{a['multiplier']:.1f}×"
        amt = "—" if a["advisory_only"] else f"{a['suggest_amount']:,.0f} 元"
        rows.append(
            "<tr>"
            f"<td style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05);color:#e8e8ec'>{_esc(a['name'])}</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05)'>{a['score']:.1f}</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05);color:var(--dim2)'>"
            f"{(a.get('band_pos') or 50):.0f}%</td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05);color:var(--gold-l)'>"
            f"<b style='font-weight:550'>{mult}</b></td>"
            f"<td class='num' style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05)'>"
            f"{amt}</td>"
            f"<td class='mono' style='padding:9px 10px;border-bottom:1px solid rgba(255,255,255,.05);color:var(--dim)'>"
            f"{_esc(ex.get('fund_code') or '—')}</td>"
            "</tr>")
    summary = ("<table style='width:100%;border-collapse:collapse;font-size:12.5px'>"
               "<thead><tr style='color:var(--dim3);font-size:9.5px;text-align:left;"
               "letter-spacing:.16em;text-transform:uppercase'>"
               "<th style='padding:0 10px 9px;font-weight:400'>标的</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>分数</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>档内</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>倍数</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>建议金额</th>"
               "<th style='padding:0 10px 9px;font-weight:400'>落地基金</th>"
               "</tr></thead><tbody style='color:var(--txt)'>" + "".join(rows) + "</tbody></table>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#000000">
<meta name="color-scheme" content="dark">
<title>定投台 · {_esc(latest['trade_date'])}</title>
<style>{CSS}</style></head>
<body><div class="wrap">

<div class="hd">
  <div class="brand"><h1>定投台</h1><span class="en">DCA Dashboard</span></div>
  <div class="meta" id="meta"></div>
</div>

<div class="hero" id="hero"></div>
<div class="macro" id="macro"></div>
<div class="grid" id="grid"></div>

<h2>本期结论 <small>分数越高越该买 · 50 分 = 1.0 倍</small></h2>
<div class="notes">{summary}</div>

<h2>分数历史 <small>中性带宽 40–56 分 · 虚线为 1.0 倍基准</small></h2>
<div class="chart" id="chart"></div>

<h2>口径与数据来源</h2>
<div class="notes">
  <ul>
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
    · 黄金价格分位为名义口径，未做通胀调整
  </div>
  <ul>
    <li><b>数据来源</b>：MSCI 官方指数接口（106801 / 990100）· 新浪财经 US_MinKService（.IXIC/.NDX/.INX）·
        东方财富 push2his（GC00Y/000922/000300/UDI/USDCNH）· 美国财政部 official CSV（TIPS 与名义收益率）·
        蛋卷基金 index_eva（PE 周频序列 + PB 分位）· 天天基金（净值与申购状态）</li>
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
