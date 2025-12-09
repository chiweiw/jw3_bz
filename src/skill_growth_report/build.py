import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

from .parser import find_skills, extract_sequences
from .analyzer import analyze, diffs
from .db import init_db, upsert_skill, upsert_series, replace_values, upsert_analysis
from .export import export_all, ensure_dir


def unique_label(existing: Dict[str, Any], label: str) -> str:
    if label not in existing:
        return label
    i = 2
    while True:
        cand = f"{label}#{i}"
        if cand not in existing:
            return cand
        i += 1


def run(input_fp: Path, site_dir: Path, db_path: Path, jump_threshold: float) -> None:
    text = input_fp.read_text(encoding="utf-8")
    skills_blocks = find_skills(text)
    ensure_dir(site_dir)
    conn = sqlite3.connect(str(db_path))
    init_db(conn)
    skills_out: List[Dict[str, Any]] = []
    series_out: List[Dict[str, Any]] = []
    values_out: Dict[str, List[Dict[str, Any]]] = {}
    analyses_out: Dict[str, Dict[str, Any]] = {}
    for name, sid, start, end in skills_blocks:
        block = text[start:end]
        seqs = extract_sequences(block)
        upsert_skill(conn, sid, name, json.dumps({"start": start, "end": end}))
        skills_out.append({"skill_id": sid, "name": name})
        store: Dict[str, Any] = {}
        for item in seqs:
            label = unique_label(store, item["label"])
            store[label] = item["values"]
            series_id = f"{sid}:{label}"
            upsert_series(conn, series_id, sid, label, item["units"], json.dumps({}))
            ds = diffs(item["values"]) if len(item["values"]) > 1 else []
            rows: List[Dict[str, Any]] = []
            for idx, v in enumerate(item["values"], start=1):
                d = None
                if idx > 1:
                    d = v - item["values"][idx - 2]
                rows.append({"level_index": idx, "value": v, "diff_to_prev": d, "is_jump": False})
            a = analyze(item["values"], jump_threshold)
            for jp in a["jump_points"]:
                if 1 <= jp <= len(rows):
                    rows[jp - 1]["is_jump"] = True
            replace_values(conn, series_id, rows)
            upsert_analysis(conn, series_id, a, json.dumps(a["jump_points"]))
            series_out.append({"series_id": series_id, "skill_id": sid, "label": label, "units": item["units"], "meta": {}})
            values_out[series_id] = rows
            analyses_out[series_id] = a
    conn.commit()
    conn.close()
    export_all(site_dir, skills_out, series_out, values_out, analyses_out)
    copy_frontend(site_dir)


def copy_frontend(site_dir: Path) -> None:
    assets_dir = site_dir / "assets"
    ensure_dir(assets_dir)
    (site_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (site_dir / "charts.html").write_text(CHARTS_HTML, encoding="utf-8")
    (assets_dir / "main.js").write_text(MAIN_JS, encoding="utf-8")
    (assets_dir / "style.css").write_text(STYLE_CSS, encoding="utf-8")


INDEX_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>技能数据增长报告</title>
  <link rel="stylesheet" href="assets/style.css" />
  <script defer src="assets/main.js"></script>
  <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Microsoft YaHei,Helvetica,Arial,sans-serif}</style>
  <script>window.PAGE='index'</script>
  <script>window.DATA_BASE='data'</script>
  <script>window.CDN_ECHARTS='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'</script>
  <script>window.LOCAL_ECHARTS='assets/echarts.min.js'</script>
  <script>(function(d,s,c,l){var e=d.createElement('script');e.src=c; e.onerror=function(){var f=d.createElement('script');f.src=l;d.head.appendChild(f)};d.head.appendChild(e)})(document,'script',window.CDN_ECHARTS,window.LOCAL_ECHARTS)</script>
  <script>(function(){if(location.protocol==='file:'){['skills','series','values','analysis'].forEach(function(n){var s=document.createElement('script');s.src='data/'+n+'.js';document.head.appendChild(s)})}})()</script>
  </head>
<body>
  <header>
    <h1>技能数据增长报告</h1>
    <div class="filters">
      <input id="q" placeholder="搜索技能名称或ID" />
      <select id="labelType">
        <option value="">全部类型</option>
        <option value="消耗">消耗</option>
        <option value="伤害">伤害</option>
        <option value="打击">打击</option>
        <option value="恢复">恢复</option>
      </select>
      <select id="sortBy">
        <option value="">默认排序</option>
        <option value="jumps">跃迁数量</option>
        <option value="max">最大值</option>
        <option value="linear">线性优先</option>
      </select>
    </div>
  </header>
  <main>
    <table id="seriesTable">
      <thead>
        <tr><th>技能</th><th>序列</th><th>区间</th><th>线性</th><th>趋势</th><th>跃迁</th><th></th></tr>
      </thead>
      <tbody></tbody>
    </table>
    <div id="details"></div>
  </main>
</body>
</html>
"""


CHARTS_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>技能数据图表</title>
  <link rel="stylesheet" href="assets/style.css" />
  <script defer src="assets/main.js"></script>
  <style>body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Microsoft YaHei,Helvetica,Arial,sans-serif}</style>
  <script>window.PAGE='charts'</script>
  <script>window.DATA_BASE='data'</script>
  <script>window.CDN_ECHARTS='https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js'</script>
  <script>window.LOCAL_ECHARTS='assets/echarts.min.js'</script>
  <script>(function(d,s,c,l){var e=d.createElement('script');e.src=c; e.onerror=function(){var f=d.createElement('script');f.src=l;d.head.appendChild(f)};d.head.appendChild(e)})(document,'script',window.CDN_ECHARTS,window.LOCAL_ECHARTS)</script>
  <script>(function(){if(location.protocol==='file:'){['skills','series','values','analysis'].forEach(function(n){var s=document.createElement('script');s.src='data/'+n+'.js';document.head.appendChild(s)})}})()</script>
  </head>
<body>
  <header>
    <h1>技能数据图表</h1>
    <div class="filters">
      <input id="q" placeholder="搜索技能名称或ID" />
      <button id="drawBtn">绘制</button>
      <label><input type="checkbox" id="showDiff">差值曲线</label>
    </div>
  </header>
  <main>
    <div id="chart" style="height:600px"></div>
  </main>
</body>
</html>
"""


MAIN_JS = """
async function loadJson(name){
  if(location.protocol==='file:'){
    if(name==='skills' && window.SKILLS) return window.SKILLS
    if(name==='series' && window.SERIES) return window.SERIES
    if(name==='values' && window.VALUES) return window.VALUES
    if(name==='analysis' && window.ANALYSIS) return window.ANALYSIS
  }
  const base = window.DATA_BASE || 'data'
  const r = await fetch(`${base}/${name}.json`)
  if(!r.ok) throw new Error('加载失败')
  return await r.json()
}

function text(t){return document.createTextNode(t)}
function el(tag, attrs){
  const e = document.createElement(tag)
  if(attrs){for(const k in attrs){e.setAttribute(k, attrs[k])}}
  return e
}

function filterType(label, type){
  if(!type) return true
  if(type==='消耗') return label.startsWith('消耗-')
  if(type==='伤害') return label.includes('伤害')
  if(type==='打击') return label.includes('打击')
  if(type==='恢复') return label.includes('恢复')
  return true
}

function sortSeries(items, by){
  if(by==='jumps') return items.sort((a,b)=>b.jumps-a.jumps)
  if(by==='max') return items.sort((a,b)=>b.max-a.max)
  if(by==='linear') return items.sort((a,b)=>Number(b.is_linear)-Number(a.is_linear))
  return items
}

async function renderIndex(){
  const skills = await loadJson('skills')
  const series = await loadJson('series')
  const values = await loadJson('values')
  const analysis = await loadJson('analysis')
  const q = document.getElementById('q')
  const typeSel = document.getElementById('labelType')
  const sortSel = document.getElementById('sortBy')
  const tbody = document.querySelector('#seriesTable tbody')
  const details = document.getElementById('details')
  function apply(){
    const query = (q.value||'').trim()
    const type = typeSel.value
    const by = sortSel.value
    const skillMap = Object.fromEntries(skills.map(s=>[s.skill_id,s.name]))
    const items = []
    for(const s of series){
      const sid = s.series_id
      const a = analysis[sid]||{}
      const name = skillMap[s.skill_id]||''
      const match = !query || sid.includes(query) || name.includes(query)
      if(!match) continue
      if(!filterType(s.label, type)) continue
      const vals = values[sid]||[]
      const min = vals.length? Math.min(...vals.map(v=>v.value)) : null
      const max = vals.length? Math.max(...vals.map(v=>v.value)) : null
      const jumps = vals.filter(v=>v.is_jump).length
      items.push({sid,name,label:s.label,min,max,is_linear:a.is_linear||false,trend:a.trend||'mixed',jumps})
    }
    sortSeries(items, by)
    tbody.innerHTML = ''
    for(const it of items){
      const tr = el('tr')
      const td1 = el('td'); td1.appendChild(text(`${it.name} (${it.sid.split(':')[0]})`))
      const td2 = el('td'); td2.appendChild(text(it.label))
      const td3 = el('td'); td3.appendChild(text(it.min==null||it.max==null?'-':`${it.min} - ${it.max}`))
      const td4 = el('td'); td4.appendChild(text(it.is_linear?'是':'否'))
      const td5 = el('td'); td5.appendChild(text(it.trend))
      const td6 = el('td'); td6.appendChild(text(String(it.jumps)))
      const td7 = el('td'); const btn = el('button'); btn.textContent = '展开'; btn.onclick=()=>showDetails(it.sid, values[it.sid]||[]); td7.appendChild(btn)
      tr.append(td1,td2,td3,td4,td5,td6,td7)
      tbody.appendChild(tr)
    }
  }
  function showDetails(sid, vals){
    details.innerHTML = ''
    const table = el('table')
    const thead = el('thead')
    const trh = el('tr')
    for(const h of ['级次','值','差值','跃迁']){const th=el('th'); th.textContent=h; trh.appendChild(th)}
    thead.appendChild(trh)
    const tb = el('tbody')
    for(const v of vals){
      const tr = el('tr')
      const td1 = el('td'); td1.textContent=String(v.level_index)
      const td2 = el('td'); td2.textContent=String(v.value)
      const td3 = el('td'); td3.textContent=v.diff_to_prev==null?'-':String(v.diff_to_prev)
      const td4 = el('td'); td4.textContent=v.is_jump?'✓':''
      tr.append(td1,td2,td3,td4)
      tb.appendChild(tr)
    }
    table.append(thead,tb)
    details.appendChild(table)
  }
  q.oninput = apply
  typeSel.onchange = apply
  sortSel.onchange = apply
  apply()
}

async function renderCharts(){
  const skills = await loadJson('skills')
  const series = await loadJson('series')
  const values = await loadJson('values')
  const analysis = await loadJson('analysis')
  const q = document.getElementById('q')
  const showDiff = document.getElementById('showDiff')
  const chartEl = document.getElementById('chart')
  const chart = echarts.init(chartEl)
  function apply(){
    const query = (q.value||'').trim()
    const skillMap = Object.fromEntries(skills.map(s=>[s.skill_id,s.name]))
    const selected = series.filter(s=>!query || s.series_id.includes(query) || (skillMap[s.skill_id]||'').includes(query))
    const grid = {left:50,right:20,top:40,bottom:40}
    const opt = {title:{text:'序列折线图'},tooltip:{trigger:'axis'},legend:{},grid,xAxis:{type:'category'},yAxis:{type:'value'},series:[]}
    const maxLen = Math.max(0,...selected.map(s=>values[s.series_id]?.length||0))
    opt.xAxis.data = Array.from({length:maxLen}).map((_,i)=>i+1)
    for(const s of selected){
      const vals = values[s.series_id]||[]
      const name = `${skillMap[s.skill_id]||''} ${s.label}`
      const data = showDiff.checked? vals.slice(1).map(v=>v.diff_to_prev||0) : vals.map(v=>v.value)
      opt.series.push({name,type:'line',data})
      const a = analysis[s.series_id]||{}
      if(a.is_linear){
        opt.series[opt.series.length-1].lineStyle = {color:'#2e7d32'}
      }
      const jumps = (a.jump_points||[])
      for(const jp of jumps){
        opt.series[opt.series.length-1].markPoint = {data:[{coord:[jp, data[jp-1]], value:'跳'}]}
      }
    }
    chart.setOption(opt)
  }
  document.getElementById('drawBtn').onclick = apply
  apply()
}

function boot(){
  if(window.PAGE==='index') renderIndex()
  else renderCharts()
}
document.addEventListener('DOMContentLoaded', boot)
"""


STYLE_CSS = """
body{margin:0;padding:0;background:#fff;color:#222}
header{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-bottom:1px solid #eee}
.filters{display:flex;gap:8px}
main{padding:16px}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #ddd;padding:6px 8px;text-align:left}
thead{background:#f7f7f7}
button{padding:6px 10px}
input,select{padding:6px 8px}
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="1.txt")
    p.add_argument("--site-dir", default="报告站点")
    p.add_argument("--db-path", default="skill_report.db")
    p.add_argument("--jump-threshold", type=float, default=2.0)
    args = p.parse_args()
    run(Path(args.input), Path(args.site_dir), Path(args.db_path), args.jump_threshold)


if __name__ == "__main__":
    main()

