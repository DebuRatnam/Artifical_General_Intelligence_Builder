import { Activity, Cpu, Radio, Zap, RefreshCw } from 'lucide-react'

// Stable hash → hue, so each learned label gets its own banner color
// without a hard-coded color table.
function hueFromLabel(s = '') {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h % 360
}

export default function StatusBar({
  health,
  connected,
  latest,
  observing,
  onObserve,
  onForceVlm,
}) {
  const tactile  = latest?.tactile?.label ?? null
  const directive = latest?.tactile?.directive ?? 'Awaiting tactile signal'
  const hue = hueFromLabel(tactile || 'idle')
  const tactileGrad = tactile
    ? `linear-gradient(135deg, hsl(${hue} 70% 18%) 0%, hsl(${(hue + 40) % 360} 60% 24%) 100%)`
    : 'linear-gradient(135deg, #18181b 0%, #27272a 100%)'

  return (
    <header className="flex items-stretch gap-3 mb-3">
      {/* Brand + hardware status chips */}
      <div className="panel flex items-center gap-4 px-4 py-2.5 flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-violet-400 shadow-[0_0_8px_2px_rgba(167,139,250,0.7)]" />
          <span className="font-semibold tracking-tight">PIA</span>
          <span className="text-xs text-zinc-500 font-mono">grounded.world.model</span>
        </div>

        <div className="h-5 w-px bg-zinc-800" />

        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span className={`chip ${connected ? 'chip-live' : 'chip-mute'}`}>
            <Radio size={11} /> WS {connected ? 'LIVE' : 'OFFLINE'}
          </span>
          <span className="chip">
            <Cpu size={11} /> {health?.mock ? 'MOCK' : 'SERIAL'}
            <span className="text-zinc-500">·</span>
            <span className="text-zinc-300">460800 baud</span>
          </span>
          <span className="chip">
            <Activity size={11} /> ts <span className="text-zinc-100">{latest?.timestamp_ms ?? '—'}</span>
          </span>
          <span className="chip">
            obj <span className="text-zinc-100">{health?.objects ?? 0}</span>
            <span className="text-zinc-500">·</span>
            mem <span className="text-zinc-100">{health?.memory_size ?? 0}</span>
          </span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button className="btn" onClick={onObserve} disabled={observing}>
            <RefreshCw size={13} className={observing ? 'animate-spin' : ''} />
            Quick observe
          </button>
          <button className="btn btn-primary" onClick={onForceVlm} disabled={observing}>
            <Zap size={13} /> Observe scene
          </button>
        </div>
      </div>

      {/* Dynamic tactile classification card */}
      <div
        className="panel min-w-[280px] max-w-[360px] px-4 py-2.5 flex flex-col justify-center
                   transition-[background] duration-500 ease-out animate-fade-in"
        style={{ background: tactileGrad }}
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-300/80">Tactile contact</span>
          <span className="ml-auto chip bg-black/30 border-white/10 text-zinc-200">
            σ {latest?.tactile?.distance_sigma?.toFixed?.(2) ?? '—'}
          </span>
        </div>
        <div className="text-lg font-semibold text-white truncate">
          {tactile ?? 'No signature matched'}
        </div>
        <div className="text-[11px] font-mono text-zinc-300/80 truncate">
          {directive}
        </div>
      </div>
    </header>
  )
}
