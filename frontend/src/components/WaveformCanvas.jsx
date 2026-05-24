import { useEffect, useRef } from 'react'

import { readSeries } from '../hooks/useHardwareTelemetry.js'

/**
 * WaveformCanvas
 * Canvas-based glowing waveform plotter. Reads directly from the
 * ring-buffer ref every animation frame — never touches React state,
 * so the parent re-rendering is decoupled from the draw rate.
 *
 * Features:
 *  • HiDPI-aware (devicePixelRatio scaling).
 *  • Neon glow via two-pass stroke (wide blur + tight core line).
 *  • Auto-rescales y-axis to the running [min, max] of the window.
 *  • Subtle grid backdrop matches the rest of the dashboard theme.
 */
export default function WaveformCanvas({
  buffersRef,
  field,           // 'accel' | 'fft'
  color = '#a78bfa',
  height = 96,
  windowSize = 240,
  label,
  unit,
  format = (v) => v.toFixed(3),
}) {
  const canvasRef  = useRef(null)
  const valueRef   = useRef(null)   // <span> for the live readout — bypasses React
  const minRef     = useRef(Infinity)
  const maxRef     = useRef(-Infinity)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    let rafId = 0
    let alive = true

    // HiDPI-aware sizing. Use ResizeObserver to keep the backing store
    // in sync with the CSS box (parent column resizes etc.).
    const fit = () => {
      const dpr = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      canvas.width  = Math.max(1, Math.floor(rect.width  * dpr))
      canvas.height = Math.max(1, Math.floor(rect.height * dpr))
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    fit()
    const ro = new ResizeObserver(fit)
    ro.observe(canvas)

    const draw = () => {
      if (!alive) return
      rafId = requestAnimationFrame(draw)

      const buffers = buffersRef.current
      if (!buffers || buffers.size === 0) {
        const W = canvas.clientWidth, H = canvas.clientHeight
        ctx.clearRect(0, 0, W, H)
        drawGrid(ctx, W, H)
        return
      }

      const series = readSeries(buffers, field, windowSize)
      const W = canvas.clientWidth
      const H = canvas.clientHeight
      ctx.clearRect(0, 0, W, H)
      drawGrid(ctx, W, H)
      if (series.length < 2) return

      // Adaptive y-bounds: track a slow EMA of the running min/max so
      // the trace doesn't jitter on every new sample's extremum.
      let lo = Infinity, hi = -Infinity
      for (let i = 0; i < series.length; i++) {
        const v = series[i]
        if (v < lo) lo = v
        if (v > hi) hi = v
      }
      const prevMin = isFinite(minRef.current) ? minRef.current : lo
      const prevMax = isFinite(maxRef.current) ? maxRef.current : hi
      const smoothMin = prevMin * 0.9 + lo * 0.1
      const smoothMax = prevMax * 0.9 + hi * 0.1
      minRef.current = smoothMin
      maxRef.current = smoothMax

      const pad  = (smoothMax - smoothMin) * 0.15 || 1
      const yLo  = smoothMin - pad
      const yHi  = smoothMax + pad
      const span = yHi - yLo || 1
      const step = W / (series.length - 1)

      const project = (i, v) => {
        const x = i * step
        const y = H - ((v - yLo) / span) * (H - 8) - 4
        return [x, y]
      }

      // Gradient fill under the curve.
      ctx.beginPath()
      ctx.moveTo(0, H)
      for (let i = 0; i < series.length; i++) {
        const [x, y] = project(i, series[i])
        if (i === 0) ctx.lineTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.lineTo(W, H)
      ctx.closePath()
      const grad = ctx.createLinearGradient(0, 0, 0, H)
      grad.addColorStop(0,   hexWithAlpha(color, 0.35))
      grad.addColorStop(1,   hexWithAlpha(color, 0.0))
      ctx.fillStyle = grad
      ctx.fill()

      // Outer glow pass — wide, low-alpha.
      ctx.shadowColor = color
      ctx.shadowBlur  = 14
      ctx.strokeStyle = hexWithAlpha(color, 0.55)
      ctx.lineWidth   = 2.4
      ctx.lineJoin    = 'round'
      ctx.lineCap     = 'round'
      ctx.beginPath()
      for (let i = 0; i < series.length; i++) {
        const [x, y] = project(i, series[i])
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()

      // Tight core line — sharper, higher alpha, narrower blur.
      ctx.shadowBlur  = 4
      ctx.strokeStyle = color
      ctx.lineWidth   = 1.25
      ctx.beginPath()
      for (let i = 0; i < series.length; i++) {
        const [x, y] = project(i, series[i])
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
      ctx.shadowBlur = 0

      // Leading-edge dot.
      const lastV = series[series.length - 1]
      const [lx, ly] = project(series.length - 1, lastV)
      ctx.fillStyle = color
      ctx.shadowColor = color
      ctx.shadowBlur  = 10
      ctx.beginPath()
      ctx.arc(lx, ly, 2.6, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0

      if (valueRef.current) {
        valueRef.current.textContent = format(lastV)
      }
    }
    rafId = requestAnimationFrame(draw)

    return () => {
      alive = false
      cancelAnimationFrame(rafId)
      ro.disconnect()
    }
  }, [buffersRef, field, color, windowSize, format])

  return (
    <div className="px-4 py-3 border-b border-zinc-800 last:border-b-0">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] uppercase tracking-[0.18em] text-zinc-400 font-semibold">
          {label}
        </span>
        <div className="font-mono">
          <span ref={valueRef} className="text-zinc-100 text-sm font-semibold">—</span>
          <span className="text-zinc-500 text-[10px] ml-1">{unit}</span>
        </div>
      </div>
      <div className="relative" style={{ height }}>
        <canvas ref={canvasRef} className="w-full h-full block" />
      </div>
    </div>
  )
}

function drawGrid(ctx, W, H) {
  ctx.strokeStyle = 'rgba(63, 63, 70, 0.35)'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let i = 1; i < 4; i++) {
    const y = (H / 4) * i
    ctx.moveTo(0, y)
    ctx.lineTo(W, y)
  }
  ctx.stroke()
}

// Convert "#rrggbb" + alpha → "rgba(r,g,b,a)". Accepts 3- or 6-digit hex.
function hexWithAlpha(hex, a) {
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}
