import { useEffect, useState } from 'react'
import { Cpu } from 'lucide-react'

const POLL_MS = 500

export default function BoardCameraFeed() {
  const [src, setSrc] = useState(null)
  const [stale, setStale] = useState(false)

  useEffect(() => {
    let cancelled = false
    let currentObjectUrl = null

    const tick = async () => {
      try {
        const res = await fetch(`/api/board_camera/snapshot?t=${Date.now()}`)
        if (!res.ok) {
          if (!cancelled) setStale(true)
          return
        }
        const blob = await res.blob()
        if (cancelled) return
        const url = URL.createObjectURL(blob)
        setSrc((prev) => {
          if (prev) URL.revokeObjectURL(prev)
          return url
        })
        currentObjectUrl = url
        setStale(false)
      } catch {
        if (!cancelled) setStale(true)
      }
    }

    tick()
    const id = setInterval(tick, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
      if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl)
    }
  }, [])

  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Cpu size={14} className="text-emerald-300" />
          <span className="panel-title">Board camera (T5AI)</span>
        </div>
        <span className="text-[10px] font-mono text-zinc-500">
          {stale ? 'stale' : 'live'} · 240×240 · ~2 fps
        </span>
      </div>

      <div className="relative aspect-square bg-black/60 overflow-hidden">
        {src ? (
          <img
            src={src}
            alt="board camera"
            className="absolute inset-0 w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
            <Cpu size={32} strokeWidth={1.2} />
            <span className="text-xs mt-2 font-mono">
              {stale ? 'waiting for board JPEG …' : 'no frames yet'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
