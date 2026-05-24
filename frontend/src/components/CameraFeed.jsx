import { Camera, ScanLine } from 'lucide-react'

export default function CameraFeed({ summary, observing, lastObservedAt }) {
  return (
    <div className="panel flex flex-col">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Camera size={14} className="text-violet-300" />
          <span className="panel-title">Egocentric camera</span>
        </div>
        <span className="text-[10px] font-mono text-zinc-500">
          {lastObservedAt ? new Date(lastObservedAt).toLocaleTimeString() : '— : — : —'}
        </span>
      </div>

      <div className="relative aspect-video bg-black/60 grid-bg overflow-hidden">
        {/* Frames are captured server-side per /api/observe call. The
            placeholder shows scanline animation while observing. */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600">
          <Camera size={32} strokeWidth={1.2} />
          <span className="text-xs mt-2 font-mono">no preview — host-side capture</span>
        </div>

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

      <div className="px-4 py-2.5 border-t border-zinc-800 text-[11px] font-mono text-zinc-400 min-h-[44px]">
        {summary?.trim() ? summary : 'No VLM summary yet — click Observe scene.'}
      </div>
    </div>
  )
}
