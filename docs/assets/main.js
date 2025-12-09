async function loadJson(name){
  const fromWindow = ()=>{
    if(name==='skills' && window.SKILLS) return window.SKILLS
    if(name==='series' && window.SERIES) return window.SERIES
    if(name==='values' && window.VALUES) return window.VALUES
    if(name==='analysis' && window.ANALYSIS) return window.ANALYSIS
    return null
  }
  const loadScript = (src)=> new Promise((resolve, reject)=>{
    const s = document.createElement('script'); s.src = src; s.onload = resolve; s.onerror = reject; document.head.appendChild(s)
  })
  if(location.protocol==='file:'){
    const v = fromWindow(); if(v) return v
    await loadScript(`data/${name}.js`)
    const v2 = fromWindow(); if(v2) return v2
    throw new Error('加载失败')
  }
  const base = window.DATA_BASE || 'data'
  try{
    const r = await fetch(`${base}/${name}.json`)
    if(!r.ok) throw new Error('fetch失败')
    return await r.json()
  }catch(e){
    const v = fromWindow(); if(v) return v
    try{ await loadScript(`data/${name}.js`) } catch(_) {}
    const v2 = fromWindow(); if(v2) return v2
    throw e
  }
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
