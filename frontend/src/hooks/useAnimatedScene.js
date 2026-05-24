import { useEffect, useRef, useState } from 'react'

/**
 * useAnimatedScene
 * Smoothly interpolates incoming /api/observe scene snapshots toward
 * an animated render-state. Each object glides from its previous (x,y)
 * to the new target with critical-damped EMA. Confidence and hand
 * pose also interpolate so the arena never snaps between frames.
 *
 * Why not pure CSS transitions? CSS transitions reset when the source
 * value changes mid-flight (e.g. a fast Observe cadence) — they always
 * re-run from current position. That works, but jitter accumulates if
 * positions ping-pong. A JS interpolator with a single target gives a
 * steadier feel and lets us animate confidence/wash radius in lock-step.
 *
 * The hook returns `animatedScene` which mirrors the server payload
 * but with smoothed coordinates. New objects fade in at full target;
 * objects that disappear are decayed in place via the server's
 * existing confidence half-life (already handled server-side).
 */
export function useAnimatedScene(targetScene, { smoothing = 0.18 } = {}) {
  const [animated, setAnimated] = useState(null)
  const stateRef = useRef(new Map())   // label → { x, y, confidence, icon, ... }
  const handRef  = useRef(null)
  const targetRef = useRef(targetScene)
  targetRef.current = targetScene

  useEffect(() => {
    if (!targetScene) return
    // Seed any unseen labels at their target position so the first
    // appearance isn't an awkward glide from (0,0).
    const cur = stateRef.current
    for (const o of targetScene.objects ?? []) {
      if (!cur.has(o.label)) {
        cur.set(o.label, { x: o.x, y: o.y, confidence: 0, icon: o.icon })
      }
    }
    // Drop labels no longer in the scene snapshot (server already
    // decayed them past the threshold).
    const present = new Set((targetScene.objects ?? []).map((o) => o.label))
    for (const key of cur.keys()) if (!present.has(key)) cur.delete(key)

    if (targetScene.hand && !handRef.current) {
      handRef.current = { ...targetScene.hand }
    }
  }, [targetScene])

  useEffect(() => {
    let rafId = 0
    let alive = true

    const step = () => {
      if (!alive) return
      rafId = requestAnimationFrame(step)
      const target = targetRef.current
      if (!target) return

      const a = smoothing
      const cur = stateRef.current
      const targets = new Map((target.objects ?? []).map((o) => [o.label, o]))

      // EMA toward target for each known object.
      for (const [label, s] of cur.entries()) {
        const t = targets.get(label)
        if (!t) continue
        s.x          = s.x          + (t.x          - s.x         ) * a
        s.y          = s.y          + (t.y          - s.y         ) * a
        s.confidence = s.confidence + ((t.confidence ?? 0) - s.confidence) * a
        s.icon       = t.icon || s.icon
      }

      // Hand glides too.
      if (target.hand) {
        if (!handRef.current) handRef.current = { x: target.hand.x, y: target.hand.y }
        else {
          handRef.current.x += (target.hand.x - handRef.current.x) * a
          handRef.current.y += (target.hand.y - handRef.current.y) * a
        }
      } else {
        handRef.current = null
      }

      setAnimated({
        ...target,
        objects: (target.objects ?? []).map((o) => {
          const s = cur.get(o.label)
          return s ? { ...o, x: s.x, y: s.y, confidence: s.confidence } : o
        }),
        hand: handRef.current ? { ...handRef.current } : null,
      })
    }
    rafId = requestAnimationFrame(step)
    return () => { alive = false; cancelAnimationFrame(rafId) }
  }, [smoothing])

  return animated ?? targetScene
}
