import { useEffect, useRef, useState } from 'react'

/**
 * useHardwareTelemetry
 * Optimized WebSocket consumer for /ws/telemetry.
 *
 * Design:
 *  • Typed-array ring buffers for accel/fft/timestamp — O(1) writes,
 *    no GC churn from a growing Array.push().
 *  • Packets arrive at 30–60 Hz; React state would re-render the whole
 *    tree per packet (wasteful). Instead we batch into a ref and only
 *    bump a "latestVersion" counter at ~20 Hz via requestAnimationFrame,
 *    decoupling render rate from packet rate.
 *  • Auto-reconnects with exponential backoff capped at 4s.
 *
 * Consumers read `buffersRef.current` inside their own rAF loop
 * (Canvas waveform) and don't need to subscribe to re-renders.
 * Components that DO want re-renders (status chips, raw packet view)
 * read `latest` / `version`.
 */
export function useHardwareTelemetry({ capacity = 512, displayHz = 20 } = {}) {
  const [connected, setConnected] = useState(false)
  const [latest,    setLatest]    = useState(null)
  const [version,   setVersion]   = useState(0)

  // Ring buffers — never reallocated.
  const buffersRef = useRef({
    capacity,
    size: 0,             // number of valid samples so far (≤ capacity)
    head: 0,             // next write index (mod capacity)
    ts:    new Float64Array(capacity),
    accel: new Float32Array(capacity),
    fft:   new Float32Array(capacity),
  })

  // Holds the most-recent packet for the throttled state push.
  const pendingRef = useRef(null)
  const dirtyRef   = useRef(false)

  useEffect(() => {
    let ws
    let alive = true
    let backoff = 500
    let reconnectTimer

    const open = () => {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${proto}//${location.host}/ws/telemetry`)

      ws.onopen = () => {
        setConnected(true)
        backoff = 500
      }
      ws.onclose = () => {
        setConnected(false)
        if (!alive) return
        reconnectTimer = setTimeout(open, backoff)
        backoff = Math.min(backoff * 2, 4000)
      }
      ws.onerror = () => { try { ws.close() } catch {} }

      ws.onmessage = (ev) => {
        let pkt
        try { pkt = JSON.parse(ev.data) } catch { return }

        const b = buffersRef.current
        const i = b.head
        b.ts[i]    = pkt.timestamp_ms ?? 0
        b.accel[i] = pkt.accel_g       ?? 0
        b.fft[i]   = pkt.fft_peak_hz   ?? 0
        b.head     = (i + 1) % b.capacity
        if (b.size < b.capacity) b.size += 1

        pendingRef.current = pkt
        dirtyRef.current   = true
      }
    }
    open()

    // rAF-driven throttle. Caps state updates at ~displayHz so React
    // doesn't redraw chips/tables at the WS packet rate.
    const period = 1000 / Math.max(1, displayHz)
    let lastTick = 0
    let rafId = 0
    const tick = (now) => {
      if (alive) rafId = requestAnimationFrame(tick)
      if (!dirtyRef.current) return
      if (now - lastTick < period) return
      lastTick = now
      dirtyRef.current = false
      setLatest(pendingRef.current)
      setVersion((v) => (v + 1) % 1_000_000)
    }
    rafId = requestAnimationFrame(tick)

    return () => {
      alive = false
      cancelAnimationFrame(rafId)
      clearTimeout(reconnectTimer)
      try { ws && ws.close() } catch {}
    }
  }, [capacity, displayHz])

  return { latest, connected, version, buffersRef }
}

/**
 * Snapshot the ring buffer into a contiguous linear array of the last
 * `n` samples (oldest → newest). Called by the canvas renderer once
 * per frame. Allocates a small array; no React re-render involved.
 */
export function readSeries(buffers, key, n) {
  const { size, head, capacity } = buffers
  const arr = buffers[key]
  const count = Math.min(n ?? size, size)
  const out = new Float32Array(count)
  const start = (head - count + capacity) % capacity
  for (let i = 0; i < count; i++) {
    out[i] = arr[(start + i) % capacity]
  }
  return out
}
