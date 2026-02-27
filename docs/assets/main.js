const { createApp, reactive, onMounted, ref, nextTick, computed, watch } = Vue;

function loadJson(name){
  return fetch(`data/${name}.json`).then(r=>{if(!r.ok) throw new Error('加载失败'); return r.json()})
}

function formatNumber(num) {
  if (num == null) return '-'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

createApp({
  setup(){
    const state = reactive({ 
      skills:[], series:[], values:{}, analysis:{}, 
      q:'', 
      showDiff: false,
      category: '',
      maxSeries: 0,
      compareMode: false
    })
    const selectedKeys = ref(['charts'])
    const chartEl = ref(null)
    let chartInstance = null
    
    const showSkillDropdown = ref(false)
    const skillSearch = ref('')
    const selectedSeries = ref([])
    const loading = ref(true)
    
    const skillMap = computed(() => Object.fromEntries(state.skills.map(s=>[s.skill_id,s.name])))
    
    const seriesWithDisplayName = computed(() => {
      return state.series.map(s => ({
        ...s,
        displayName: `${skillMap.value[s.skill_id] || ''} ${s.label}`
      }))
    })
    
    const filteredSeriesList = computed(() => {
      let result = seriesWithDisplayName.value
      if (skillSearch.value) {
        const search = skillSearch.value.toLowerCase()
        result = result.filter(s => s.displayName.toLowerCase().includes(search))
      }
      if (state.category) {
        result = result.filter(s => s.category === state.category)
      }
      return result
    })
    
    const compareData = computed(() => {
      if (!state.compareMode || selectedSeries.value.length === 0) return []
      return selectedSeries.value.map(sid => {
        const vals = state.values[sid] || []
        const data = state.showDiff ? vals.slice(1).map(v => v.diff_to_prev || 0) : vals.map(v => v.value)
        const validData = data.filter(v => v != null)
        if (validData.length === 0) {
          return { name: getSeriesName(sid), min: '-', max: '-', avg: '-', growth: '-' }
        }
        const min = Math.min(...validData)
        const max = Math.max(...validData)
        const sum = validData.reduce((a, b) => a + b, 0)
        const avg = sum / validData.length
        const growth = validData.length > 1 && validData[0] !== 0 
          ? ((validData[validData.length - 1] - validData[0]) / validData[0] * 100).toFixed(1)
          : 0
        return {
          name: getSeriesName(sid),
          min: formatNumber(min),
          max: formatNumber(max),
          avg: formatNumber(avg),
          growth: growth
        }
      })
    })

    const selectAllFiltered = () => {
      selectedSeries.value = filteredSeriesList.value.map(s => s.series_id)
    }

    const clearSelection = () => {
      selectedSeries.value = []
    }

    const removeSeries = (sid) => {
      selectedSeries.value = selectedSeries.value.filter(id => id !== sid)
    }

    const getSeriesName = (sid) => {
      const s = seriesWithDisplayName.value.find(item => item.series_id === sid)
      return s ? s.displayName : sid
    }

    const apply = () => {
      if(!chartInstance) return
      
      let selected = []
      if (selectedSeries.value.length > 0) {
        selected = state.series.filter(s => selectedSeries.value.includes(s.series_id))
      } else {
        const query = (state.q||'').trim()
        selected = state.series.filter(s=>!query || s.series_id.includes(query) || (skillMap.value[s.skill_id]||'').includes(query))
      }
      
      if (state.category) {
        selected = selected.filter(s => s.category === state.category)
      }
      
      if (state.maxSeries > 0 && selected.length > state.maxSeries) {
        selected = selected.slice(0, state.maxSeries)
      }
      
      const grid = {left:60,right:20,top:60,bottom:60}
      const opt = {
        title:{text:'序列折线图',left:'center',textStyle:{fontSize:16,fontWeight:600}},
        tooltip:{
          trigger:'axis',
          formatter: function(params) {
            let result = `<div style="font-weight:600;margin-bottom:4px;">第 ${params[0].axisValue} 期</div>`
            params.forEach(p => {
              result += `<div style="display:flex;justify-content:space-between;gap:20px;">
                <span>${p.marker} ${p.seriesName}</span>
                <span style="font-weight:500;">${formatNumber(p.value)}</span>
              </div>`
            })
            return result
          }
        },
        legend:{
          type:'scroll',
          bottom:10,
          pageIconSize:12,
          pageTextStyle:{fontSize:11}
        },
        grid,
        xAxis:{type:'category',axisLabel:{fontSize:11}},
        yAxis:{
          type:'value',
          axisLabel:{
            fontSize:11,
            formatter: function(value) {
              if (Math.abs(value) >= 1000000) return (value/1000000).toFixed(1) + 'M'
              if (Math.abs(value) >= 1000) return (value/1000).toFixed(1) + 'K'
              return value
            }
          }
        },
        dataZoom: [
          {type:'inside',start:0,end:100},
          {type:'slider',start:0,end:100,height:20,bottom:40}
        ],
        toolbox:{
          feature:{
            dataZoom:{yAxisIndex:'none'},
            restore:{},
            saveAsImage:{}
          },
          right:20,
          top:10
        },
        series:[]
      }
      
      const maxLen = Math.max(0,...selected.map(s=>state.values[s.series_id]?.length||0))
      opt.xAxis.data = Array.from({length:maxLen}).map((_,i)=>i+1)
      
      for(const s of selected){
        const vals = state.values[s.series_id]||[]
        const name = `${skillMap.value[s.skill_id]||''} ${s.label}`
        const data = state.showDiff? vals.slice(1).map(v=>v.diff_to_prev||0) : vals.map(v=>v.value)
        opt.series.push({name,type:'line',data,smooth:true,symbol:'circle',symbolSize:4})
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

    const resetChart = () => {
      selectedSeries.value = []
      state.category = ''
      state.maxSeries = 0
      state.showDiff = false
      state.compareMode = false
      state.q = ''
      skillSearch.value = ''
      if (chartInstance) {
        chartInstance.clear()
        chartInstance = null
      }
      loading.value = true
      setTimeout(() => {
        initChart()
      }, 100)
    }

    const initChart = () => {
      if(chartEl.value){
        chartInstance = echarts.init(chartEl.value)
        window.addEventListener('resize', ()=>chartInstance && chartInstance.resize())
        loading.value = false
      }
    }

    watch(() => [state.category, state.maxSeries], () => {
      if (state.maxSeries > 0 && selectedSeries.value.length > state.maxSeries) {
        selectedSeries.value = selectedSeries.value.slice(0, state.maxSeries)
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

      await nextTick()
      initChart()
    })

    return { 
      state, 
      selectedKeys,
      chartEl,
      chartInstance,
      loading,
      apply,
      resetChart,
      showSkillDropdown,
      skillSearch,
      selectedSeries,
      filteredSeriesList,
      selectAllFiltered,
      clearSelection,
      removeSeries,
      getSeriesName,
      compareData
    }
  }
})
.mount('#app')
