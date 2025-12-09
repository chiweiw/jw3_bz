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
    const state = reactive({ skills:[], series:[], values:{}, analysis:{}, q:'', type:'', sort:'', expanded:{} })
    const skillMap = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id,s.name])))
    const skillMeta = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id, s.meta||{}])))
    const rows = computed(()=>{
      const items = []
      const bySkill = {}
      for(const s of state.series){
        (bySkill[s.skill_id] ||= []).push(s)
      }
      for(const sid in bySkill){
        const name = skillMap.value[sid]||''
        const match = !state.q || sid.includes(state.q) || name.includes(state.q)
        if(!match) continue
        const meta = skillMeta.value[sid]||{}
        const seriesList = bySkill[sid]
        const collect = (pred)=>{
          const vals = []
          for(const s of seriesList){
            if(!pred(s)) continue
            const vs = state.values[s.series_id]||[]
            for(const v of vs){ vals.push(v.value) }
          }
          if(!vals.length) return {min:null,max:null}
          return {min:Math.min(...vals), max:Math.max(...vals)}
        }
        let consume = collect(s=>s.label.startsWith('消耗-'))
        if(meta.threefold_no_spirit_cost){ consume = {min:0, max:0} }
        const deal = collect(s=>s.label.includes('伤害'))
        items.push({sid, name, consume_min:consume.min, consume_max:consume.max, deal_min:deal.min, deal_max:deal.max})
      }
      return items
    })
    const detailsMap = computed(()=>{
      const map = {}
      const bySkill = {}
      for(const s of state.series){ (bySkill[s.skill_id] ||= []).push(s) }
      for(const sid in bySkill){
        const res = {consume:[], deal:[], other:[]}
        for(const s of bySkill[sid]){
          const vs = state.values[s.series_id]||[]
          const item = {label:s.label, rows:vs}
          if(s.label.startsWith('消耗-')) res.consume.push(item)
          else if(s.label.includes('伤害')) res.deal.push(item)
          else res.other.push(item)
        }
        map[sid] = res
      }
      return map
    })
    const toggle = (sid)=>{ state.expanded[sid] = !state.expanded[sid] }
    onMounted(async ()=>{
      const [skills, series, values, analysis] = await Promise.all([
        loadJson('skills'), loadJson('series'), loadJson('values'), loadJson('analysis')
      ])
      state.skills = skills
      state.series = series
      state.values = values
      state.analysis = analysis
    })
    return { state, rows, detailsMap, toggle }
  },
  template: `
    <section>
      <div class='filters'>
        <input v-model.trim="state.q" placeholder="搜索技能名称或ID" />
      </div>
      <table>
        <thead>
          <tr><th>技能</th><th>消耗区间</th><th>造成区间</th><th></th></tr>
        </thead>
        <tbody>
          <template v-for="it in rows" :key="it.sid">
            <tr>
              <td>{{ it.name }} ({{ it.sid }})</td>
              <td>{{ (it.consume_min==null||it.consume_max==null)? '-' : (it.consume_min + ' - ' + it.consume_max) }}</td>
              <td>{{ (it.deal_min==null||it.deal_max==null)? '-' : (it.deal_min + ' - ' + it.deal_max) }}</td>
              <td>
                <button @click="toggle(it.sid)">{{ state.expanded[it.sid] ? '收起' : '展开' }}</button>
              </td>
            </tr>
            <tr v-if="state.expanded[it.sid]">
              <td colspan="4">
                <div>
                  <h3>消耗明细</h3>
                  <div v-for="grp in detailsMap[it.sid].consume" :key="grp.label" style="margin-bottom:12px">
                    <h4>{{ grp.label }}</h4>
                    <table>
                      <thead>
                        <tr><th>级次</th><th>值</th><th>差值</th><th>跃迁</th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="v in grp.rows" :key="v.level_index">
                          <td>{{ v.level_index }}</td>
                          <td>{{ v.value }}</td>
                          <td>{{ v.diff_to_prev==null? '-' : v.diff_to_prev }}</td>
                          <td>{{ v.is_jump ? '✓' : '' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <h3>造成明细</h3>
                  <div v-for="grp in detailsMap[it.sid].deal" :key="grp.label" style="margin-bottom:12px">
                    <h4>{{ grp.label }}</h4>
                    <table>
                      <thead>
                        <tr><th>级次</th><th>值</th><th>差值</th><th>跃迁</th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="v in grp.rows" :key="v.level_index">
                          <td>{{ v.level_index }}</td>
                          <td>{{ v.value }}</td>
                          <td>{{ v.diff_to_prev==null? '-' : v.diff_to_prev }}</td>
                          <td>{{ v.is_jump ? '✓' : '' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <h3 v-if="detailsMap[it.sid].other.length">其他明细</h3>
                  <div v-for="grp in detailsMap[it.sid].other" :key="grp.label" style="margin-bottom:12px">
                    <h4>{{ grp.label }}</h4>
                    <table>
                      <thead>
                        <tr><th>级次</th><th>值</th><th>差值</th><th>跃迁</th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="v in grp.rows" :key="v.level_index">
                          <td>{{ v.level_index }}</td>
                          <td>{{ v.value }}</td>
                          <td>{{ v.diff_to_prev==null? '-' : v.diff_to_prev }}</td>
                          <td>{{ v.is_jump ? '✓' : '' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div style="margin-top:12px"></div>
    </section>
  `
}).mount('#app')
