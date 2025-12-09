const { createApp, reactive, onMounted, computed, ref } = Vue

function loadJson(name){
  return fetch(`data/${name}.json`).then(r=>{if(!r.ok) throw new Error('加载失败'); return r.json()})
}

createApp({
  setup(){
    const selectedKeys = ref(['index'])
    const state = reactive({ skills:[], series:[], values:{}, analysis:{}, q:'', type:'', sort:'', expanded:{} })
    const skillMap = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id,s.name])))
    const skillMeta = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id, s.meta||{}])))
    const skillDesc = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id, s.description||''])))

    const columns = [
      { title: '技能', key: 'name', dataIndex: 'name', width: 200 },
      { title: '技能描述', key: 'description', dataIndex: 'description' },
      { title: '消耗区间', key: 'consume', dataIndex: 'consume', width: 150 },
      { title: '造成区间', key: 'deal', dataIndex: 'deal', width: 150 },
    ]

    const detailColumns = [
      { title: '级次', dataIndex: 'level_index', width: 80 },
      { title: '数值', dataIndex: 'value' },
      { title: '差值', dataIndex: 'diff_to_prev' },
      { title: '跃迁', key: 'is_jump', dataIndex: 'is_jump', width: 80 },
    ]

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
        const desc = skillDesc.value[sid]||''
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
        items.push({sid, name, description: desc, consume_min:consume.min, consume_max:consume.max, deal_min:deal.min, deal_max:deal.max, meta})
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
    
    return { state, rows, detailsMap, toggle, columns, detailColumns, selectedKeys }
  }
})
.use(antd)
.mount('#app')