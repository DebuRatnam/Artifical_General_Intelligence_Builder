import { Map as MapIcon, Volume2, Hand } from 'lucide-react'

import { useAnimatedScene } from '../hooks/useAnimatedScene.js'

// Server returns x,y in [0,1] with y=0 at the bottom. CSS top grows
// downward, so we invert y when placing each marker.
function place(x, y) {
  return {
    left: `${Math.max(0, Math.min(1, x)) * 100}%`,
    top:  `${(1 - Math.max(0, Math.min(1, y))) * 100}%`,
    transform: 'translate(-50%, -50%)',
  }
}

export default function WorldMap({ scene }) {
  // rAF-driven EMA toward the latest /api/observe payload. Markers
  // glide instead of snapping when the VLM returns a new layout.
  const smooth = useAnimatedScene(scene, { smoothing: 0.16 })

  const objects = smooth?.objects ?? []
  const sounds  = smooth?.audio_sources ?? []
  const hand    = smooth?.hand ?? null

  const emitterFreq = new Map(sounds.map((s) => [s.label.toLowerCase(), s.freq_hz]))

  return (
    <div className="panel flex flex-col min-h-0 flex-1">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <MapIcon size={14} className="text-violet-300" />
          <span className="panel-title">Grounded 2D arena</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500">
          <span className="chip">{objects.length} obj</span>
          <span className="chip">{sounds.length} src</span>
          {smooth?.last_used_fast_path !== undefined && (
            <span className={`chip ${smooth.last_used_fast_path ? 'text-emerald-300' : 'text-violet-300'}`}>
              {smooth.last_used_fast_path ? 'FAST · CLIP' : 'SLOW · VLM'}
            </span>
          )}
        </div>
      </div>

      {/* Audio source strip */}
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center gap-2 flex-wrap min-h-[44px]">
        <Volume2 size={12} className="text-zinc-500" />
        {sounds.length === 0 ? (
          <span className="text-[11px] font-mono text-zinc-600">no bound emitters</span>
        ) : (
          sounds.map((s) => (
            <span key={s.label} className="chip">
              <span>{s.icon}</span>
              <span className="text-zinc-200">{s.label}</span>
              <span className="text-zinc-500">·</span>
              <span className="text-violet-300">{s.freq_hz} Hz</span>
            </span>
          ))
        )}
      </div>

      {/* Arena */}
      <div className="relative flex-1 min-h-[360px] grid-bg overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          {['top-left','top-right','bottom-left','bottom-right'].map((corner) => {
            const [v,h] = corner.split('-')
            return (
              <span key={corner}
                className="absolute text-[9px] font-mono uppercase tracking-widest text-zinc-700"
                style={{
                  ...(v === 'top'    ? { top: 6 }    : { bottom: 6 }),
                  ...(h === 'left'   ? { left: 8 }   : { right: 8 }),
                }}>
                {corner}
              </span>
            )
          })}
        </div>

        {objects.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-zinc-600 text-sm font-mono">
            no objects in scene — click Observe scene
          </div>
        )}

        {objects.map((o) => {
          const isEmitter = emitterFreq.has(o.label.toLowerCase())
          const opacity = 0.35 + 0.65 * (o.confidence ?? 0.5)
          // Short CSS transition smooths the per-frame EMA jitter
          // without overriding the per-frame target. 80ms ≈ 1 rAF block.
          return (
            <div
              key={o.label}
              className="absolute will-change-transform animate-fade-in"
              style={{
                ...place(o.x, o.y),
                opacity,
                transition: 'left 80ms linear, top 80ms linear, opacity 250ms ease-out',
              }}
            >
              <div className="relative flex flex-col items-center">
                <div
                  className="absolute rounded-full bg-violet-500/15 blur-md"
                  style={{
                    width:  `${30 + (o.confidence ?? 0) * 50}px`,
                    height: `${30 + (o.confidence ?? 0) * 50}px`,
                    transition: 'width 250ms ease-out, height 250ms ease-out',
                  }}
                />
                {isEmitter && (
                  <>
                    <div className="absolute w-12 h-12 rounded-full border border-violet-400/60 animate-pulse-ring" />
                    <div className="absolute w-12 h-12 rounded-full border border-violet-400/40 animate-pulse-ring"
                         style={{ animationDelay: '0.5s' }} />
                  </>
                )}
                <div className="relative text-3xl drop-shadow-[0_0_8px_rgba(167,139,250,0.4)] select-none">
                  {o.icon || '❓'}
                </div>
                <div className="relative mt-1 text-[10px] font-mono font-semibold text-zinc-100
                                bg-zinc-950/80 border border-zinc-800 rounded px-1.5 py-0.5">
                  {o.label}
                  <span className="ml-1 text-zinc-500">{(o.confidence ?? 0).toFixed(2)}</span>
                </div>
              </div>
            </div>
          )
        })}

        {hand && (
          <div
            className="absolute will-change-transform"
            style={{
              ...place(hand.x, hand.y),
              transition: 'left 80ms linear, top 80ms linear',
            }}
          >
            <div className="relative">
              <div className="absolute -inset-3 rounded-full border-2 border-amber-400/50 animate-pulse-ring" />
              <Hand size={26} className="text-amber-300 drop-shadow-[0_0_6px_rgba(251,191,36,0.6)]" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
