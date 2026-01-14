const { createApp, reactive, onMounted, computed, ref } = Vue

// 说明：
// - 本文件按“计算层”和“展示层”拆分，计算层只做数据加工，展示层只做 UI 绑定
// - 计算层提供纯函数，输入 state/常量，输出行数据和明细映射

// ---------------- 计算层 ----------------

// 加载站点数据（skills/series/values/analysis）
function loadJson(name){
  return fetch(`data/${name}.json`).then(r=>{if(!r.ok) throw new Error('加载失败'); return r.json()})
}

// 规范化查询串，支持全角空格与多种连字符
function normalizeText(s){ return (s||'').replace(/[\s\u3000\\-–—－_]/g,'') }
function extractId(s){ return (s||'').match(/\d{5}/)?.[0] || '' }

// 取区间（第10重及以后），若不足10重则取全部
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

// 计算消耗区间（优先 RESOURCES 中存在的键，否则回退到所有键）
function computeConsumeRange(groups, meta){
  const preferKeys = (window.RESOURCES||['精神','耐力','气血','内力']).filter(k => (groups.consume||{})[k] && (groups.consume||{})[k].length)
  const keys = preferKeys.length ? preferKeys : Object.keys(groups.consume||{})
  let rng = pickRange(groups.consume||{}, keys)
  if(meta?.threefold_no_spirit_cost){ rng = {min:0, max:0} }
  return rng
}

// 计算造成区间（优先“伤害”，其次“打击”，否则回退到所有键）
function computeDealRange(groups){
  let keys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('伤害'))
  if(!keys.length){ keys = Object.keys(groups.deal||{}).filter(k=>k.endsWith('打击')) }
  if(!keys.length){ keys = Object.keys(groups.deal||{}) }
  return pickRange(groups.deal||{}, keys)
}

// 从 skills 构建便捷映射
function buildSkillMaps(skills){
  return {
    skillMap: Object.fromEntries(skills.map(s=>[s.skill_id,s.name])),
    skillMeta: Object.fromEntries(skills.map(s=>[s.skill_id, s.meta||{}])),
    skillDesc: Object.fromEntries(skills.map(s=>[s.skill_id, s.description||''])),
    skillEffects: Object.fromEntries(skills.map(s=>[s.skill_id, s.special_effects||[]])),
    skillGroups: Object.fromEntries(skills.map(s=>[s.skill_id, s.groups||{}])),
  }
}

// 计算一条行记录
function computeRowForSkill(sid, maps){
  const name = maps.skillMap[sid]||''
  const meta = maps.skillMeta[sid]||{}
  const desc = maps.skillDesc[sid]||''
  const effects = maps.skillEffects[sid]||[]
  const effects_text = effects.join('；')
  const groups = maps.skillGroups[sid]||{}
  const consume = computeConsumeRange(groups, meta)
  const deal = computeDealRange(groups)
  const consumeStr = (consume.min!=null && consume.max!=null) ? `${consume.min} - ${consume.max}` : '-'
  const dealStr = (deal.min!=null && deal.max!=null) ? `${deal.min} - ${deal.max}` : '-'
  return {sid, name, description: desc, effects_text, consume_min:consume.min, consume_max:consume.max, deal_min:deal.min, deal_max:deal.max, meta, consume: consumeStr, deal: dealStr, effects: effects_text}
}

// 计算表格行（按 skills 遍历，查询串兼容 名称/ID/混合）
function computeRows(state){
  const maps = buildSkillMaps(state.skills)
  const q = (state.q||'').trim()
  const qId = extractId(q)
  const qNorm = normalizeText(q)
  const items = []
  for(const s of state.skills){
    const sid = s.skill_id
    const name = maps.skillMap[sid]||''
    const nameNorm = normalizeText(name)
    const match = !q || sid.includes(q) || sid.includes(qId) || name.includes(q) || nameNorm.includes(qNorm)
    if(!match) continue
    items.push(computeRowForSkill(sid, maps))
  }
  return items
}

// 计算明细映射（从 groups.consume/deal/recover 映射到 values）
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
          pack[toKey].push({label: obj.label, rows: vs})
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

// ---------------- 展示层 ----------------

// 表格列（信息页）
const columns = [
  { title: '技能', key: 'name', dataIndex: 'name', width: 200 },
  { title: '技能描述', key: 'description', dataIndex: 'description' },
  { title: '特殊效果', key: 'effects', dataIndex: 'effects_text' },
  { title: '消耗区间', key: 'consume', dataIndex: 'consume', width: 150 },
  { title: '造成区间', key: 'deal', dataIndex: 'deal', width: 150 },
]

// 展开行明细列
const detailColumns = [
  { title: '级次', dataIndex: 'level_index', width: 80 },
  { title: '数值', dataIndex: 'value' },
  { title: '差值', dataIndex: 'diff_to_prev' },
  { title: '跃迁', key: 'is_jump', dataIndex: 'is_jump', width: 80 },
]

// Vue 应用
createApp({
  setup(){
    const selectedKeys = ref(['index'])
    const state = reactive({ skills:[], series:[], values:{}, analysis:{}, q:'', type:'', sort:'', expanded:{} })
    const rows = computed(()=> computeRows(state))
    const detailsMap = computed(()=> computeDetailsMap(state))
    const expandedRowKeys = computed(()=> Object.keys(state.expanded).filter(k => state.expanded[k]))
    const toggle = (sid)=>{ state.expanded[sid] = !state.expanded[sid] }
    const onExpand = (expanded, record)=>{ state.expanded[record.sid] = expanded }
    onMounted(async ()=>{
      const [skills, series, values, analysis] = await Promise.all([
        loadJson('skills'), loadJson('series'), loadJson('values'), loadJson('analysis')
      ])
      state.skills = skills
      state.series = series
      state.values = values
      state.analysis = analysis
    })
    return { state, rows, detailsMap, toggle, columns, detailColumns, selectedKeys, expandedRowKeys, onExpand }
  }
})
.use(antd)
.mount('#app')
