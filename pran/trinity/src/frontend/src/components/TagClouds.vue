<template>
  <div class="tag-clouds-container">
    <!-- Render each tag cloud as an SVG group -->
    <svg
      v-for="cloud in tagClouds"
      :key="cloud.tag"
      class="tag-cloud"
      :style="{
        position: 'absolute',
        left: `${cloud.x}px`,
        top: `${cloud.y}px`,
        width: `${cloud.width}px`,
        height: `${cloud.height}px`,
        pointerEvents: 'none',
        zIndex: -1,
        overflow: 'visible'
      }"
    >
      <defs>
        <!-- Blur filter for softer edges -->
        <filter :id="`blur-${cloud.tag}`" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" :stdDeviation="blurAmount" />
        </filter>
      </defs>

      <!-- Cloud shape - rounded rectangle with blur -->
      <rect
        x="0"
        y="0"
        :width="cloud.width"
        :height="cloud.height"
        :rx="cloudBorderRadius"
        :ry="cloudBorderRadius"
        :fill="cloud.color"
        :filter="`url(#blur-${cloud.tag})`"
        :opacity="cloudOpacity"
      />

      <!-- Tag label (optional, shown in corner) -->
      <text
        v-if="showLabels"
        :x="labelPadding"
        :y="labelPadding + 14"
        :fill="cloud.textColor"
        font-size="12"
        font-weight="500"
        :opacity="0.8"
      >
        #{{ cloud.tag }}
      </text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  nodes: {
    type: Array,
    required: true
  },
  // Padding around the nodes in a cloud
  padding: {
    type: Number,
    default: 40
  },
  // Opacity of the cloud fill
  cloudOpacity: {
    type: Number,
    default: 0.15
  },
  // Blur amount for softer edges
  blurAmount: {
    type: Number,
    default: 20
  },
  // Border radius for the cloud shape
  cloudBorderRadius: {
    type: Number,
    default: 30
  },
  // Whether to show tag labels
  showLabels: {
    type: Boolean,
    default: true
  },
  // Padding for the label from corner
  labelPadding: {
    type: Number,
    default: 15
  },
  // Node dimensions (for bounding box calculation)
  nodeWidth: {
    type: Number,
    default: 320
  },
  nodeHeight: {
    type: Number,
    default: 270
  }
})

// Color palette for different tags - soft, distinct colors
const tagColors = [
  { bg: '#3b82f6', text: '#1e40af' },  // Blue
  { bg: '#10b981', text: '#047857' },  // Emerald
  { bg: '#f59e0b', text: '#b45309' },  // Amber
  { bg: '#ec4899', text: '#be185d' },  // Pink
  { bg: '#8b5cf6', text: '#6d28d9' },  // Violet
  { bg: '#06b6d4', text: '#0e7490' },  // Cyan
  { bg: '#f97316', text: '#c2410c' },  // Orange
  { bg: '#84cc16', text: '#4d7c0f' },  // Lime
  { bg: '#ef4444', text: '#b91c1c' },  // Red
  { bg: '#14b8a6', text: '#0f766e' },  // Teal
]

// Get a consistent color for a tag based on its name
function getTagColor(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % tagColors.length
  return tagColors[index]
}

// Compute tag clouds based on node positions
const tagClouds = computed(() => {
  // Group nodes by their tags
  const tagGroups = new Map()

  props.nodes.forEach(node => {
    const tags = node.data?.tags || []
    tags.forEach(tag => {
      if (!tagGroups.has(tag)) {
        tagGroups.set(tag, [])
      }
      tagGroups.get(tag).push(node)
    })
  })

  // Calculate bounding boxes for each tag group
  const clouds = []

  tagGroups.forEach((nodesInTag, tag) => {
    if (nodesInTag.length === 0) return

    // Calculate bounding box
    let minX = Infinity, minY = Infinity
    let maxX = -Infinity, maxY = -Infinity

    nodesInTag.forEach(node => {
      const x = node.position?.x || 0
      const y = node.position?.y || 0

      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x + props.nodeWidth)
      maxY = Math.max(maxY, y + props.nodeHeight)
    })

    // Add padding
    const padding = props.padding
    const color = getTagColor(tag)

    clouds.push({
      tag,
      x: minX - padding,
      y: minY - padding,
      width: maxX - minX + padding * 2,
      height: maxY - minY + padding * 2,
      color: color.bg,
      textColor: color.text,
      nodeCount: nodesInTag.length
    })
  })

  // Sort by area (largest first) so smaller clouds render on top
  clouds.sort((a, b) => (b.width * b.height) - (a.width * a.height))

  return clouds
})
</script>

<style scoped>
.tag-clouds-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: -1;
}

.tag-cloud {
  transition: all 0.3s ease-out;
}
</style>
