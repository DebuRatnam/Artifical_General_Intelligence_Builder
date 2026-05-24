import { useEffect, useRef, useState } from 'react'
import { MessageSquare, Send, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { api } from '../lib/api.js'

// Rotating status lines shown under the typing indicator. Cycles every
// ~1.6s while the request is in flight — gives the user a sense the
// agent is doing real grounding work, not just spinning.
const PHASES = [
  'compiling scene context',
  'reading object memory',
  'projecting tactile state',
  'invoking ollama',
  'composing reply',
]

function TypingIndicator() {
  const [phase, setPhase] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setPhase((p) => (p + 1) % PHASES.length), 1600)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="animate-fade-in">
      <div className="text-[10px] uppercase tracking-[0.18em] mb-1 text-violet-300 flex items-center gap-2">
        <Loader2 size={11} className="animate-spin" />
        &lt; agent
      </div>
      <div className="flex items-center gap-3 pl-1">
        <div className="flex gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse"
                style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse"
                style={{ animationDelay: '160ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse"
                style={{ animationDelay: '320ms' }} />
        </div>
        <span className="text-[11px] font-mono text-zinc-500">{PHASES[phase]}…</span>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [history, setHistory] = useState([])
  const [input,   setInput]   = useState('')
  const [pending, setPending] = useState(false)
  const [error,   setError]   = useState(null)
  const endRef   = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [history, pending])

  const send = async (e) => {
    e?.preventDefault?.()
    const prompt = input.trim()
    if (!prompt || pending) return
    setInput('')
    setError(null)
    const next = [...history, { role: 'user', content: prompt }]
    setHistory(next)
    setPending(true)
    try {
      const { reply } = await api.chat(prompt, history)
      setHistory([...next, { role: 'assistant', content: reply }])
    } catch (err) {
      setError(err.message)
      setHistory([...next, {
        role: 'assistant',
        content: `_chat error_ — \`${err.message}\``,
      }])
    } finally {
      setPending(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="panel flex flex-col min-h-0 flex-1">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-violet-300" />
          <span className="panel-title">Ollama terminal</span>
        </div>
        <span className={`chip ${pending ? 'chip-live' : ''}`}>
          {pending ? 'thinking…' : 'idle'}
        </span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-dark px-4 py-3 space-y-3 font-mono text-[12.5px]">
        {history.length === 0 && !pending && (
          <div className="text-zinc-500 italic">
            Ask the agent about the scene, memory, or current FFT peak…
          </div>
        )}
        {history.map((m, i) => (
          <div key={i} className="animate-fade-in">
            <div className={`text-[10px] uppercase tracking-[0.18em] mb-1 ${
              m.role === 'user' ? 'text-emerald-400' : 'text-violet-300'
            }`}>
              {m.role === 'user' ? '> user' : '< agent'}
            </div>
            <div className={`md-chat text-zinc-200 ${
              m.role === 'user' ? 'pl-3 border-l-2 border-emerald-500/40' : ''
            }`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {m.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        {pending && <TypingIndicator />}
        <div ref={endRef} />
      </div>

      {error && (
        <div className="px-4 py-2 border-t border-rose-500/30 bg-rose-500/10 text-rose-300 text-[11px] font-mono">
          {error}
        </div>
      )}

      <form onSubmit={send} className="flex items-center gap-2 p-2 border-t border-zinc-800">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={pending ? 'agent thinking…' : 'ask the agent…'}
          disabled={pending}
          className="flex-1 bg-zinc-950/80 border border-zinc-800 rounded-md px-3 py-2
                     text-[13px] font-mono placeholder-zinc-600
                     focus:outline-none focus:border-violet-500/60 focus:ring-1 focus:ring-violet-500/30
                     disabled:opacity-50"
        />
        <button type="submit" className="btn btn-primary" disabled={pending || !input.trim()}>
          {pending
            ? <Loader2 size={13} className="animate-spin" />
            : <Send    size={13} />}
          Send
        </button>
      </form>
    </div>
  )
}
