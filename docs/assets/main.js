const { createApp, reactive, onMounted, ref, nextTick } = Vue;

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

createApp({
  setup(){
    const state = reactive({ 
      skills:[], series:[], values:{}, analysis:{}, 
      q:'', 
      showDiff: false 
    })
    const selectedKeys = ref(['charts'])
    const chartEl = ref(null)
    let chartInstance = null

    const apply = () => {
      if(!chartInstance) return
      const query = (state.q||'').trim()
      const skillMap = Object.fromEntries(state.skills.map(s=>[s.skill_id,s.name]))
      const selected = state.series.filter(s=>!query || s.series_id.includes(query) || (skillMap[s.skill_id]||'').includes(query))
      const grid = {left:50,right:20,top:40,bottom:40}
      const opt = {title:{text:'序列折线图'},tooltip:{trigger:'axis'},legend:{},grid,xAxis:{type:'category'},yAxis:{type:'value'},series:[]}
      const maxLen = Math.max(0,...selected.map(s=>state.values[s.series_id]?.length||0))
      opt.xAxis.data = Array.from({length:maxLen}).map((_,i)=>i+1)
      for(const s of selected){
        const vals = state.values[s.series_id]||[]
        const name = `${skillMap[s.skill_id]||''} ${s.label}`
        const data = state.showDiff? vals.slice(1).map(v=>v.diff_to_prev||0) : vals.map(v=>v.value)
        opt.series.push({name,type:'line',data})
        const a = state.analysis[s.series_id]||{}
        if(a.is_linear){
          opt.series[opt.series.length-1].lineStyle = {color:'#2e7d32'}
        }
        const jumps = (a.jump_points||[])
        for(const jp of jumps){
          opt.series[opt.series.length-1].markPoint = {data:[{coord:[jp, data[jp-1]], value:'跳'}]}
        }
      }
      chartInstance.setOption(opt, true)
    }

    onMounted(async ()=>{
      // Load Data
      const [skills, series, values, analysis] = await Promise.all([
        loadJson('skills'), loadJson('series'), loadJson('values'), loadJson('analysis')
      ])
      state.skills = skills
      state.series = series
      state.values = values
      state.analysis = analysis

      // Init Chart
      await nextTick()
      if(chartEl.value){
        chartInstance = echarts.init(chartEl.value)
        window.addEventListener('resize', ()=>chartInstance.resize())
        apply()
      }
    })

    return { 
      state, 
      selectedKeys,
      chartEl,
      apply
    }
  }
})
.use(antd)
.mount('#app')
