import { useEffect, useRef } from 'react'
import { Camera, ScanLine } from 'lucide-react'

export default function CameraFeed({ summary, observing, lastObservedAt }) {
  const videoRef = useRef(null)

  useEffect(() => {
    let stream = null
    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then((s) => {
        stream = s
        if (videoRef.current) {
          videoRef.current.srcObject = s
        }
      })
      .catch(() => {})
    return () => {
      if (stream) stream.getTracks().forEach((t) => t.stop())
    }
  }, [])

  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Camera size={14} className="text-violet-300" />
          <span className="panel-title">Laptop camera (VLM source)</span>
        </div>
        <span className="text-[10px] font-mono text-zinc-500">
          {lastObservedAt ? new Date(lastObservedAt).toLocaleTimeString() : '— : — : —'}
        </span>
      </div>

      <div className="relative aspect-video bg-black/60 overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
        />

        {observing && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute left-0 right-0 h-1 bg-gradient-to-b from-violet-400/50 to-transparent
                            animate-[pulse-ring_2s_linear_infinite]"
                 style={{ top: '40%' }} />
            <div className="absolute top-2 left-2 chip chip-live">
              <ScanLine size={11} /> CAPTURING
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-zinc-800">
        <div className="px-4 py-1.5 flex items-center justify-between border-b border-zinc-800/60">
          <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-500">
            llava raw output
          </span>
          {summary?.trim() && (
            <span className="text-[10px] font-mono text-zinc-600">
              {summary.split('\n').filter(l => l.trim()).length} lines
            </span>
          )}
        </div>
        <div className="px-4 py-3 text-[12px] font-mono text-zinc-300 leading-relaxed
                        min-h-[160px] max-h-[280px] overflow-y-auto whitespace-pre-wrap break-words
                        bg-black/30">
          {summary?.trim() ? summary : (
            <span className="text-zinc-600">No VLM summary yet — click Observe scene.</span>
          )}
        </div>
      </div>
    </div>
  )
}
