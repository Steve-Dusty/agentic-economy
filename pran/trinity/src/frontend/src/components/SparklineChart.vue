<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, toRaw } from 'vue'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

const props = defineProps({
  // Array of values (numbers or nulls)
  data: {
    type: Array,
    required: true
  },
  // Chart color (CSS color string)
  color: {
    type: String,
    default: '#3b82f6'
  },
  // Maximum Y value for scale
  yMax: {
    type: Number,
    default: 100
  },
  // Chart dimensions
  width: {
    type: Number,
    default: 60
  },
  height: {
    type: Number,
    default: 20
  }
})

const chartEl = ref(null)
let chart = null

function createChartOpts() {
  return {
    width: props.width,
    height: props.height,
    padding: [2, 0, 2, 0],
    cursor: { show: false },
    legend: { show: false },
    select: { show: false },
    scales: {
      x: { time: false },
      y: { min: 0, max: props.yMax, range: [0, props.yMax] }
    },
    axes: [
      { show: false },
      { show: false }
    ],
    series: [
      {},
      {
        stroke: props.color,
        width: 1.5,
        fill: props.color + '30',
        spanGaps: true,
        points: { show: false }
      }
    ]
  }
}

function initChart() {
  if (!chartEl.value) return

  // Clear any existing content
  chartEl.value.innerHTML = ''

  // Generate timestamp indices (just sequential numbers since we don't show axis)
  const timestamps = props.data.map((_, i) => i)

  // Convert Vue reactive arrays to raw arrays for uPlot
  const data = [timestamps, toRaw(props.data)]
  chart = new uPlot(createChartOpts(), data, chartEl.value)
}

function updateChart() {
  if (!chart) return

  // Generate timestamp indices
  const timestamps = props.data.map((_, i) => i)
  chart.setData([timestamps, toRaw(props.data)])
}

// Watch for data changes
watch(() => props.data, () => {
  if (chart) {
    updateChart()
  }
}, { deep: true })

// Watch for color/yMax changes - need to recreate chart
watch(() => [props.color, props.yMax], () => {
  if (chart) {
    chart.destroy()
    chart = null
  }
  nextTick(() => initChart())
})

onMounted(async () => {
  await nextTick()
  initChart()
})

onUnmounted(() => {
  if (chart) {
    chart.destroy()
    chart = null
  }
})
</script>

<template>
  <span ref="chartEl" class="sparkline-chart"></span>
</template>

<style scoped>
.sparkline-chart {
  display: inline-block;
  background: rgba(107, 114, 128, 0.1);
  border-radius: 2px;
  overflow: hidden;
  vertical-align: middle;
}

/* Dark mode */
.dark .sparkline-chart {
  background: rgba(55, 65, 81, 0.5);
}

/* uPlot canvas sizing */
:deep(.uplot) {
  width: 100% !important;
}

:deep(.u-wrap) {
  width: 100% !important;
}

:deep(.u-over),
:deep(.u-under) {
  width: 100% !important;
}
</style>
