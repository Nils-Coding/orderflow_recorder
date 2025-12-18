# Frontend Setup Guide: Orderflow Visualizer

This guide describes how to set up the Frontend Web App for the Orderflow Recorder project.

## 1. Tech Stack
*   **Framework:** [Astro](https://astro.build/) (Fast, content-focused, great for dashboards).
*   **UI Library:** [Vue 3](https://vuejs.org/) (Reactive components).
*   **Styling:** [Tailwind CSS](https://tailwindcss.com/) (Utility-first CSS).
*   **Charting:** [Lightweight Charts](https://tradingview.github.io/lightweight-charts/) (High-performance financial charts by TradingView).

---

## 2. Initialization Steps

Run these commands in your terminal (outside the backend folder, or in a new `frontend` folder).

### Step 1: Create Astro Project
```bash
# Create a new project (choose 'Empty' template if asked)
npm create astro@latest orderflow-frontend

# Enter the folder
cd orderflow-frontend
```

### Step 2: Add Integrations
Astro makes it easy to add Vue and Tailwind.
```bash
# Add Vue support
npx astro add vue

# Add Tailwind CSS
npx astro add tailwind
```

### Step 3: Install Charting Library
```bash
npm install lightweight-charts
```

---

## 3. Project Structure
Recommended structure:
```
src/
├── components/
│   └── OrderflowChart.vue  <-- The main chart component
├── layouts/
│   └── Layout.astro        <-- Base HTML structure
├── pages/
│   └── index.astro         <-- Main dashboard page
└── env.d.ts
```

---

## 4. Starter Code: Chart Component

Create `src/components/OrderflowChart.vue`. This component fetches data from your Cloud API and renders it.

```vue
<script setup>
import { onMounted, ref, onUnmounted } from 'vue';
import { createChart, ColorType } from 'lightweight-charts';

const chartContainer = ref(null);
const loading = ref(true);
const error = ref(null);

// Configuration (Should be in .env in production)
const API_URL = import.meta.env.PUBLIC_API_URL || 'https://YOUR-CLOUD-RUN-URL/api/v1/candles';
const API_KEY = import.meta.env.PUBLIC_API_KEY || 'YOUR_API_KEY';

onMounted(async () => {
  if (!chartContainer.value) return;

  // 1. Initialize Chart
  const chart = createChart(chartContainer.value, {
    layout: {
      background: { type: ColorType.Solid, color: '#1a1a1a' },
      textColor: '#d1d5db',
    },
    grid: {
      vertLines: { color: '#333' },
      horzLines: { color: '#333' },
    },
    width: chartContainer.value.clientWidth,
    height: 600,
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  });

  const volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: 'volume' },
    priceScaleId: '', // Overlay on same scale or separate? Usually separate pane.
  });
  
  // To put volume in a separate pane below, we need a separate chart or careful scaling.
  // For simplicity V1, let's overlay or just stick to candles first.
  // Lightweight charts supports panes by creating multiple charts or custom logic.

  // 2. Fetch Data
  try {
    const url = `${API_URL}?symbol=btcusdt&date=2025-12-11&resolution=1m`;
    const response = await fetch(url, {
      headers: { 'X-API-Key': API_KEY }
    });
    
    if (!response.ok) throw new Error(`API Error: ${response.status}`);
    
    const json = await response.json();
    const data = json.data;

    // 3. Transform for Lightweight Charts
    // Expected format: { time: 1642425322, open: ..., high: ..., low: ..., close: ... }
    const candles = data.map(d => ({
      time: d.time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    candleSeries.setData(candles);
    
    // Fit content
    chart.timeScale().fitContent();

  } catch (err) {
    console.error(err);
    error.value = err.message;
  } finally {
    loading.value = false;
  }

  // Cleanup
  const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({ width: chartContainer.value.clientWidth });
  });
  resizeObserver.observe(chartContainer.value);
  
  onUnmounted(() => {
      chart.remove();
      resizeObserver.disconnect();
  });
});
</script>

<template>
  <div class="relative w-full h-[600px] border border-gray-700 rounded-lg overflow-hidden">
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-gray-900 text-white z-10">
      Loading Data...
    </div>
    <div v-if="error" class="absolute inset-0 flex items-center justify-center bg-red-900/50 text-red-200 z-10">
      {{ error }}
    </div>
    <div ref="chartContainer" class="w-full h-full bg-[#1a1a1a]"></div>
  </div>
</template>
```

### Step 5: Use it in Astro
In `src/pages/index.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
import OrderflowChart from '../components/OrderflowChart.vue';
---

<Layout title="Orderflow Dashboard">
	<main class="container mx-auto p-4 bg-gray-900 min-h-screen text-white">
		<h1 class="text-3xl font-bold mb-6">Bitcoin Orderflow (Daily)</h1>
		
		<!-- Client:only is crucial for Vue components using window/document -->
		<OrderflowChart client:only="vue" />
	</main>
</Layout>
```

