const { createApp, reactive, onMounted, computed, ref, watch } = Vue

function loadJson(name){
  return fetch(`data/${name}.json`).then(r=>{if(!r.ok) throw new Error('加载失败'); return r.json()})
}

function normalizeText(s){ return (s||'').replace(/[\s\u3000\\-–—－_]/g,'') }
function extractId(s){ return (s||'').match(/\d{5}/)?.[0] || '' }

function formatNumber(num){
  if(num == null) return '-'
  return num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function pickRange(bucket, keys){
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

function computeConsumeRange(groups, meta){
  const preferKeys = (window.RESOURCES||['精神','耐力','气血','内力']).filter(k => (groups.consume||{})[k] && (groups.consume||{})[k].length)
  const keys = preferKeys.length ? preferKeys : Object.keys(groups.consume||{})
  let rng = pickRange(groups.consume||{}, keys)
  if(meta?.threefold_no_spirit_cost){ rng = {min:0, max:0} }
  return rng
}

function computeDealRange(groups){
  let keys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('伤害'))
  if(!keys.length){ keys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('打击')) }
  if(!keys.length){ keys = Object.keys(groups.deal||{}) }
  return pickRange(groups.deal||{}, keys)
}

function buildSkillMaps(skills){
  return {
    skillMap: Object.fromEntries(skills.map(s=>[s.skill_id,s.name])),
    skillMeta: Object.fromEntries(skills.map(s=>[s.skill_id, s.meta||{}])),
    skillDesc: Object.fromEntries(skills.map(s=>[s.skill_id, s.description||''])),
    skillEffects: Object.fromEntries(skills.map(s=>[s.skill_id, s.special_effects||[]])),
    skillGroups: Object.fromEntries(skills.map(s=>[s.skill_id, s.groups||{}])),
  }
}

function computeRowForSkill(sid, maps){
  const name = maps.skillMap[sid]||''
  const meta = maps.skillMeta[sid]||{}
  const desc = maps.skillDesc[sid]||''
  const effects = maps.skillEffects[sid]||[]
  const effects_text = effects.join('；')
  const groups = maps.skillGroups[sid]||{}
  const consume = computeConsumeRange(groups, meta)
  const deal = computeDealRange(groups)
  const consumeStr = (consume.min!=null && consume.max!=null) ? `${formatNumber(consume.min)} - ${formatNumber(consume.max)}` : '-'
  const dealStr = (deal.min!=null && deal.max!=null) ? `${formatNumber(deal.min)} - ${formatNumber(deal.max)}` : '-'
  return {sid, name, description: desc, effects_text, consume_min:consume.min, consume_max:consume.max, deal_min:deal.min, deal_max:deal.max, meta, consume: consumeStr, deal: dealStr, effects: effects_text}
}

function computeRows(state){
  const maps = buildSkillMaps(state.skills)
  const q = (state.q||'').trim().toLowerCase()
  const qId = extractId(q)
  const qNorm = normalizeText(q)
  const items = []
  for(const s of state.skills){
    const sid = s.skill_id
    const name = maps.skillMap[sid]||''
    const meta = maps.skillMeta[sid]||{}
    const nameNorm = normalizeText(name).toLowerCase()
    
    let match = false
    if(!q) match = true
    else if(sid.includes(q)) match = true
    else if(qId && sid.includes(qId)) match = true
    else if(name.toLowerCase().includes(q)) match = true
    else if(nameNorm.includes(qNorm)) match = true
    
    if(state.filterThreefold && !meta.has_threefold) match = false
    if(state.filterStealSpirit && !meta.steal_spirit) match = false
    
    if(!match) continue
    items.push(computeRowForSkill(sid, maps))
  }
  return items
}

function computeDetailsMap(state){
  const maps = buildSkillMaps(state.skills)
  const res = {}
  for(const s of state.skills){
    const sid = s.skill_id
    const groups = maps.skillGroups[sid]||{}
    const pack = {consume:[], deal:[], other:[]}
    const attach = (bucket, toKey) => {
      const keys = Object.keys(bucket||{})
      for(const k of keys){
        const lst = bucket[k]||[]
        for(const obj of lst){
          const seriesId = `${sid}:${obj.label}`
          const vs = state.values[seriesId]||[]
          const formattedRows = vs.map(v => ({
            ...v,
            value_formatted: formatNumber(v.value),
            diff_to_prev_formatted: formatNumber(v.diff_to_prev)
          }))
          pack[toKey].push({label: obj.label, rows: formattedRows})
        }
      }
    }
    attach(groups.consume||{}, 'consume')
    attach(groups.deal||{}, 'deal')
    attach(groups.recover||{}, 'other')
    res[sid] = pack
  }
  return res
}

const HISTORY_KEY = 'skill_search_history'
const MAX_HISTORY = 10

function loadHistory(){
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch { return [] }
}

function saveHistory(history){
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
}

createApp({
  setup(){
    const selectedKeys = ref(['index'])
    const state = reactive({ 
      skills:[], series:[], values:{}, analysis:{}, 
      q:'', sortKey: '', sortOrder: 'asc',
      filterThreefold: false, filterStealSpirit: false,
      expanded: {} 
    })
    const sectionExpanded = reactive({})
    const showSearchHistory = ref(false)
    const searchHistory = ref(loadHistory())
    
    const rows = computed(()=> computeRows(state))
    const detailsMap = computed(()=> computeDetailsMap(state))
    const expandedRowKeys = computed(()=> Object.keys(state.expanded).filter(k => state.expanded[k]))
    
    const sortedRows = computed(() => {
      const items = [...rows.value]
      if(!state.sortKey) return items
      const order = state.sortOrder === 'asc' ? 1 : -1
      return items.sort((a, b) => {
        if(state.sortKey === 'name'){
          return a.name.localeCompare(b.name, 'zh-CN') * order
        }
        if(state.sortKey === 'consume'){
          const aVal = a.consume_min ?? Infinity
          const bVal = b.consume_min ?? Infinity
          return (aVal - bVal) * order
        }
        if(state.sortKey === 'deal'){
          const aVal = a.deal_min ?? Infinity
          const bVal = b.deal_min ?? Infinity
          return (aVal - bVal) * order
        }
        return 0
      })
    })
    
    const toggleSort = (key) => {
      if(state.sortKey === key){
        state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc'
      } else {
        state.sortKey = key
        state.sortOrder = 'asc'
      }
    }
    
    const toggle = (sid)=>{ 
      state.expanded[sid] = !state.expanded[sid]
      if(state.expanded[sid]){
        const d = detailsMap.value[sid]
        if(!sectionExpanded[sid]){
           sectionExpanded[sid] = {
               consume: d && d.consume.length > 0,
               deal: d && d.deal.length > 0,
               other: d && d.other.length > 0
           }
        }
      }
    }
    
    const toggleSection = (sid, key) => {
        if(sectionExpanded[sid]){
            sectionExpanded[sid][key] = !sectionExpanded[sid][key]
        }
    }
    
    const highlightText = (text, query) => {
      if(!query || !text) return text
      const q = query.trim()
      if(!q) return text
      const regex = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
      return text.replace(regex, '<span class="highlight">$1</span>')
    }
    
    const getConsumeColorClass = (min, max) => {
      if(min === 0 && max === 0) return 'bg-green-50 text-green-700 border-green-200'
      const avg = (min + max) / 2
      if(avg < 100) return 'bg-green-50 text-green-700 border-green-200'
      if(avg < 500) return 'bg-yellow-50 text-yellow-700 border-yellow-200'
      if(avg < 2000) return 'bg-orange-50 text-orange-700 border-orange-200'
      return 'bg-red-50 text-red-700 border-red-200'
    }
    
    const getDealColorClass = (min, max) => {
      const avg = (min + max) / 2
      if(avg < 10000) return 'bg-blue-50 text-blue-700 border-blue-200'
      if(avg < 50000) return 'bg-indigo-50 text-indigo-700 border-indigo-200'
      if(avg < 200000) return 'bg-purple-50 text-purple-700 border-purple-200'
      return 'bg-pink-50 text-pink-700 border-pink-200'
    }
    
    const hideSearchHistory = () => {
      setTimeout(() => { showSearchHistory.value = false }, 200)
    }
    
    const selectHistory = (item) => {
      state.q = item
      showSearchHistory.value = false
    }
    
    const removeHistory = (idx) => {
      searchHistory.value.splice(idx, 1)
      saveHistory(searchHistory.value)
    }
    
    watch(() => state.q, (val) => {
      const q = val?.trim()
      if(q && q.length >= 1){
        const idx = searchHistory.value.indexOf(q)
        if(idx > -1) searchHistory.value.splice(idx, 1)
        searchHistory.value.unshift(q)
        if(searchHistory.value.length > MAX_HISTORY){
          searchHistory.value.pop()
        }
        saveHistory(searchHistory.value)
      }
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
    
    return { 
      state, rows, sortedRows, detailsMap, toggle, selectedKeys, expandedRowKeys, 
      sectionExpanded, toggleSection, toggleSort,
      showSearchHistory, searchHistory, hideSearchHistory, selectHistory, removeHistory,
      highlightText, getConsumeColorClass, getDealColorClass
    }
  }
})
.mount('#app')
