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
    const skillEffects = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id, s.special_effects||[]])))
    const skillGroups = computed(()=>Object.fromEntries(state.skills.map(s=>[s.skill_id, s.groups||{}])))

    const columns = [
      { title: '技能', key: 'name', dataIndex: 'name', width: 200 },
      { title: '技能描述', key: 'description', dataIndex: 'description' },
      { title: '特殊效果', key: 'effects', dataIndex: 'effects_text' },
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
        const q = (state.q||'').trim()
        const qId = (q.match(/\d{5}/)||[])[0]||''
        const qNorm = q.replace(/\s|-/g,'')
        const nameNorm = (name||'').replace(/\s/g,'')
        const match = !q || sid.includes(q) || sid.includes(qId) || name.includes(q) || nameNorm.includes(qNorm)
        if(!match) continue
        const meta = skillMeta.value[sid]||{}
        const desc = skillDesc.value[sid]||''
        const effects = skillEffects.value[sid]||[]
        const effects_text = effects.join('；')
        const groups = skillGroups.value[sid]||{}
        const pickRange = (bucket, keys)=>{
          const vals = []
          for(const k of keys){
            const lst = (bucket?.[k])||[]
            for(const obj of lst){
              const arr = obj.values||[]
              if(arr.length >= 10){
                for(let i=9;i<arr.length;i++){ vals.push(arr[i]) }
              }else{
                for(const v of arr){ vals.push(v) }
              }
            }
          }
          if(!vals.length) return {min:null,max:null}
          return {min:Math.min(...vals), max:Math.max(...vals)}
        }
        const preferConsumeKeys = (window.RESOURCES||['精神','耐力','气血','内力']).filter(k => (groups.consume||{})[k] && (groups.consume||{})[k].length)
        const consumeKeys = preferConsumeKeys.length ? preferConsumeKeys : Object.keys(groups.consume||{})
        let consume = pickRange(groups.consume||{}, consumeKeys)
        if(meta.threefold_no_spirit_cost){ consume = {min:0, max:0} }
        let dealKeys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('伤害'))
        if(!dealKeys.length){ dealKeys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('打击')) }
        if(!dealKeys.length){ dealKeys = Object.keys(groups.deal||{}) }
        const deal = pickRange(groups.deal||{}, dealKeys)
        items.push({sid, name, description: desc, effects_text, consume_min:consume.min, consume_max:consume.max, deal_min:deal.min, deal_max:deal.max, meta})
      }
      return items
    })
    
    const detailsMap = computed(()=>{
      const map = {}
      const bySkill = {}
      for(const s of state.series){ (bySkill[s.skill_id] ||= []).push(s) }
      for(const sid in bySkill){
        const res = {consume:[], deal:[], other:[]}
        const groups = skillGroups.value[sid]||{}
        const attach = (bucket, toKey) => {
          const keys = Object.keys(bucket||{})
          for(const k of keys){
            const lst = bucket[k]||[]
            for(const obj of lst){
              const seriesId = `${sid}:${obj.label}`
              const vs = state.values[seriesId]||[]
              res[toKey].push({label: obj.label, rows: vs})
            }
          }
        }
        attach(groups.consume||{}, 'consume')
        attach(groups.deal||{}, 'deal')
        attach(groups.recover||{}, 'other')
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
