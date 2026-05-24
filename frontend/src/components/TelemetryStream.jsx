import { Waves, Database } from 'lucide-react'

import WaveformCanvas from './WaveformCanvas.jsx'

export default function TelemetryStream({ buffersRef, latest, memorySize, version }) {
  const sampleCount = buffersRef?.current?.size ?? 0

  return (
    <div className="panel flex flex-col flex-1 min-h-0">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <Waves size={14} className="text-violet-300" />
          <span className="panel-title">Telemetry streams</span>
        </div>
        <span className="chip">{sampleCount} pts</span>
      </div>

      <WaveformCanvas
        buffersRef={buffersRef}
        field="accel"
        color="#a78bfa"
        label="Acceleration"
        unit="g"
        format={(v) => v.toFixed(3)}
      />
      <WaveformCanvas
        buffersRef={buffersRef}
        field="fft"
        color="#38bdf8"
        label="FFT peak"
        unit="Hz"
        format={(v) => `${Math.round(v)}`}
      />

      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-dark p-3 font-mono text-[11px] text-zinc-400">
        <div className="flex items-center gap-2 mb-2 text-zinc-500">
          <Database size={11} /> last packet <span className="ml-auto text-zinc-600">v{version}</span>
        </div>
        <pre className="bg-zinc-950/80 border border-zinc-800 rounded p-2 whitespace-pre-wrap break-all">
{JSON.stringify(latest ?? {}, null, 2)}
        </pre>
        <div className="mt-3 flex items-center justify-between text-zinc-500">
          <span>memory size</span>
          <span className="text-zinc-200">{memorySize ?? 0}</span>
        </div>
      </div>
    </div>
  )
}
