import { useCallback, useEffect, useState } from 'react'

import StatusBar       from './components/StatusBar.jsx'
import CameraFeed      from './components/CameraFeed.jsx'
import BoardCameraFeed from './components/BoardCameraFeed.jsx'
import ChatPanel       from './components/ChatPanel.jsx'
import WorldMap        from './components/WorldMap.jsx'
import TelemetryStream from './components/TelemetryStream.jsx'

import { useHardwareTelemetry } from './hooks/useHardwareTelemetry.js'
import { api } from './lib/api.js'

export default function App() {
  const { latest, connected, version, buffersRef } =
    useHardwareTelemetry({ capacity: 512, displayHz: 20 })

  const [health,    setHealth]    = useState(null)
  const [scene,     setScene]     = useState(null)
  const [summary,   setSummary]   = useState('')
  const [observing, setObserving] = useState(false)
  const [lastObservedAt, setLastObservedAt] = useState(null)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const h = await api.health()
        if (alive) setHealth(h)
      } catch {}
    }
    tick()
    const id = setInterval(tick, 3000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  const observe = useCallback(async (force_vlm = false) => {
    if (observing) return
    setObserving(true)
    try {
      const res = await api.observe(force_vlm)
      setScene(res.scene)
      setSummary(res.summary)
      setLastObservedAt(Date.now())
    } catch (err) {
      setSummary(`(observe failed: ${err.message})`)
    } finally {
      setObserving(false)
    }
  }, [observing])

  return (
    <div className="h-full w-full p-3 flex flex-col">
      <StatusBar
        health={health}
        connected={connected}
        latest={latest}
        observing={observing}
        onObserve={()    => observe(false)}
        onForceVlm={()   => observe(true)}
      />

      <main className="flex-1 min-h-0 grid grid-cols-12 gap-3">
        <section className="col-span-3 flex flex-col gap-3 min-h-0">
          <CameraFeed
            summary={summary}
            observing={observing}
            lastObservedAt={lastObservedAt}
          />
          <BoardCameraFeed />
          <ChatPanel />
        </section>

        <section className="col-span-6 flex flex-col min-h-0">
          <WorldMap scene={scene} />
        </section>

        <section className="col-span-3 flex flex-col min-h-0">
          <TelemetryStream
            buffersRef={buffersRef}
            latest={latest}
            version={version}
            memorySize={health?.memory_size}
          />
        </section>
      </main>
    </div>
  )
}
