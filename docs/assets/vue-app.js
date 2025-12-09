
const { createApp, reactive, onMounted, computed } = Vue

function loadJson(name){
  if(location.protocol==='file:'){
    if(name==='skills' && window.SKILLS) return Promise.resolve(window.SKILLS)
    if(name==='series' && window.SERIES) return Promise.resolve(window.SERIES)
    if(name==='values' && window.VALUES) return Promise.resolve(window.VALUES)
    if(name==='analysis' && window.ANALYSIS) return Promise.resolve(window.ANALYSIS)
  }
  const base = window.DATA_BASE || 'data'
  return fetch(`${base}/${name}.json`).then(r=>{if(!r.ok) throw new Error('加载失败'); return r.json()})
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

createApp({
  setup(){
    const state = reactive({ skills:[], series:[], values:{}, analysis:{}, q:'', type:'', sort:'' , selected:null })
    const skillMap = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id,s.name])))
    const rows = computed(()=>{
      const items = []
      for(const s of state.series){
        const sid = s.series_id
        const a = state.analysis[sid]||{}
        const name = skillMap.value[s.skill_id]||''
        const match = !state.q || sid.includes(state.q) || name.includes(state.q)
        if(!match) continue
        if(!filterType(s.label, state.type)) continue
        const vals = state.values[sid]||[]
        const min = vals.length? Math.min(...vals.map(v=>v.value)) : null
        const max = vals.length? Math.max(...vals.map(v=>v.value)) : null
        const jumps = vals.filter(v=>v.is_jump).length
        items.push({sid,name,label:s.label,min,max,is_linear:a.is_linear||false,trend:a.trend||'mixed',jumps})
      }
      return sortSeries(items, state.sort)
    })
    const details = computed(()=>{
      if(!state.selected) return []
      return state.values[state.selected]||[]
    })
    onMounted(async ()=>{
      const [skills, series, values, analysis] = await Promise.all([
        loadJson('skills'), loadJson('series'), loadJson('values'), loadJson('analysis')
      ])
      state.skills = skills
      state.series = series
      state.values = values
      state.analysis = analysis
    })
    return { state, rows, details }
  },
  template: `
    <section>
      <div class='filters'>
        <input v-model.trim="state.q" placeholder="搜索技能名称或ID" />
        <select v-model="state.type">
          <option value="">全部类型</option>
          <option value="消耗">消耗</option>
          <option value="伤害">伤害</option>
          <option value="打击">打击</option>
          <option value="恢复">恢复</option>
        </select>
        <select v-model="state.sort">
          <option value="">默认排序</option>
          <option value="jumps">跃迁数量</option>
          <option value="max">最大值</option>
          <option value="linear">线性优先</option>
        </select>
      </div>
      <table>
        <thead>
          <tr><th>技能</th><th>序列</th><th>区间</th><th>线性</th><th>趋势</th><th>跃迁</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="it in rows" :key="it.sid">
            <td>{{ it.name }} ({{ it.sid.split(':')[0] }})</td>
            <td>{{ it.label }}</td>
            <td>{{ (it.min==null||it.max==null)? '-' : (it.min + ' - ' + it.max) }}</td>
            <td>{{ it.is_linear ? '是' : '否' }}</td>
            <td>{{ it.trend }}</td>
            <td>{{ String(it.jumps) }}</td>
            <td><button @click="state.selected = it.sid">展开</button></td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top:12px">
        <table v-if="details.length">
          <thead>
            <tr><th>级次</th><th>值</th><th>差值</th><th>跃迁</th></tr>
          </thead>
          <tbody>
            <tr v-for="v in details" :key="v.level_index">
              <td>{{ v.level_index }}</td>
              <td>{{ v.value }}</td>
              <td>{{ v.diff_to_prev==null? '-' : v.diff_to_prev }}</td>
              <td>{{ v.is_jump ? '✓' : '' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `
}).mount('#app')
