/**
 * UCS VISUALISATION -- Module 5, the search itself.
 *
 * Steps through the trace the Python engine recorded while it ran. Nothing here
 * is reconstructed or re-simulated in JavaScript: each step is a snapshot the
 * algorithm emitted at one removal from its priority queue, so what is shown is
 * what the search actually did.
 *
 * At each step: the node removed, its cumulative cost g(n), the priority queue,
 * the locations already expanded, and every neighbour considered with the
 * reason it was kept or rejected.
 */

import { useEffect, useState } from 'react'

export default function UCSVisualizationPanel({ search, onStepChange }) {
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)

  const trace = search?.trace ?? []
  const step = trace[index]

  // A new search resets the walkthrough to the beginning.
  useEffect(() => {
    setIndex(0)
    setPlaying(false)
  }, [search])

  // Tell the map which node is being expanded, so it can be highlighted there.
  useEffect(() => {
    if (!step) {
      onStepChange(null)
      return
    }
    onStepChange({
      node: step.node,
      explored: step.explored,
      frontier: step.frontierAfter,
    })
  }, [step, onStepChange])

  useEffect(() => {
    if (!playing) return undefined
    if (index >= trace.length - 1) {
      setPlaying(false)
      return undefined
    }
    const timer = setTimeout(() => setIndex((current) => current + 1), 900)
    return () => clearTimeout(timer)
  }, [playing, index, trace.length])

  if (!search || trace.length === 0) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h2>Uniform Cost Search</h2>
          <span className="module-tag">Module 5 · AI engine</span>
        </div>
        <div className="empty-state">
          The search trace appears here once a route has been requested.
          <br />
          Every step the algorithm takes is recorded and can be replayed.
        </div>
      </div>
    )
  }

  const atStart = index === 0
  const atEnd = index >= trace.length - 1

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Uniform Cost Search</h2>
        <span className="module-tag">Module 5 · AI engine</span>
      </div>

      <div className="ucs-controls">
        <button
          type="button" className="small ghost"
          onClick={() => { setPlaying(false); setIndex(0) }}
          disabled={atStart}
        >
          ↺ Restart
        </button>
        <button
          type="button" className="small ghost"
          onClick={() => { setPlaying(false); setIndex((i) => Math.max(0, i - 1)) }}
          disabled={atStart}
        >
          ◀ Prev
        </button>
        <button
          type="button" className="small"
          onClick={() => setPlaying((p) => !p)}
          disabled={atEnd && !playing}
        >
          {playing ? '⏸ Pause' : '▶ Play'}
        </button>
        <button
          type="button" className="small ghost"
          onClick={() => {
            setPlaying(false)
            setIndex((i) => Math.min(trace.length - 1, i + 1))
          }}
          disabled={atEnd}
        >
          Next ▶
        </button>
        <span className="step-count">
          step {index + 1} / {trace.length}
        </span>
      </div>

      <div className="panel-body tight">
        <div className="step-line">
          <span className={`action-tag ${step.action}`}>
            {step.action === 'expand' && 'expand'}
            {step.action === 'discard' && 'skip'}
            {step.action === 'goal' && 'goal reached'}
          </span>
          <span className="current-node">{step.node}</span>
          <span className="g-value">
            g(n) = <b>{step.cumulativeCost}</b> min
          </span>
        </div>

        {/* -------- the priority queue -------- */}
        <div className="sub-label">
          Priority queue{step.action === 'goal' ? ' (after termination)' : ''} — ordered by g(n)
        </div>
        <div className="queue">
          {step.frontierAfter.length === 0 && (
            <div className="queue-empty">(empty — the search has finished)</div>
          )}
          {step.frontierAfter.map((entry, position) => (
            <div
              key={`${entry.node}-${entry.cost}-${position}`}
              className={
                `queue-entry ${position === 0 && !entry.stale ? 'head' : ''} `
                + `${entry.stale ? 'stale' : ''}`
              }
            >
              <span className="qn">{entry.node}</span>
              {entry.stale && <span className="qtag">obsolete</span>}
              <span className="qc">{entry.cost}</span>
            </div>
          ))}
        </div>

        {/* -------- neighbours considered -------- */}
        {step.successors.length > 0 && (
          <>
            <div className="sub-label">Neighbours of {step.node}</div>
            <div>
              {step.successors.map((successor) => (
                <div
                  key={successor.node}
                  className={`successor ${successor.accepted ? 'accepted' : 'rejected'}`}
                >
                  <span className="sn">{successor.node}</span>
                  <span className="smath">
                    {step.cumulativeCost} + {successor.edgeCost} = {successor.newCost}
                  </span>
                  <span className="sreason">
                    {successor.accepted ? '✓ ' : '✕ '}
                    {successor.reason}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        {/* -------- expanded so far -------- */}
        <div className="sub-label">
          Expanded so far ({step.explored.length})
        </div>
        <div className="chip-row">
          {step.explored.length === 0 && (
            <span style={{ color: 'var(--text-faint)', fontSize: 11.5 }}>none yet</span>
          )}
          {step.explored.map((node) => (
            <span key={node} className={`chip ${node === step.node ? 'current' : ''}`}>
              {node}
            </span>
          ))}
        </div>

        {step.note && <div className="step-note">{step.note}</div>}

        {/* -------- the answer -------- */}
        {step.action === 'goal' && (
          <>
            <div className="sub-label">Final route</div>
            <div className="route-chain" style={{ marginBottom: 0 }}>
              {step.path.map((node, position) => (
                <span key={`${node}-${position}`} style={{ display: 'contents' }}>
                  {position > 0 && <span className="chain-arrow">→</span>}
                  <span
                    className={
                      `chain-node ${position === 0 || position === step.path.length - 1
                        ? 'endpoint' : ''}`
                    }
                  >
                    {node}
                  </span>
                </span>
              ))}
              <span className="chain-arrow" style={{ marginLeft: 6 }}>=</span>
              <span className="chain-node endpoint">{step.cumulativeCost} min</span>
            </div>
          </>
        )}
      </div>

      <div className="ucs-summary">
        <span>removals: <b>{search.pops}</b></span>
        <span>expanded: <b>{search.exploredCount}</b></span>
        <span>obsolete entries skipped: <b>{search.staleDiscards}</b></span>
        <span>total cost: <b>{search.totalCost}</b></span>
      </div>

      <div className="explain">
        Priority is the cumulative path cost <strong>g(n)</strong> alone — there is no
        heuristic, which is what makes this Uniform Cost Search rather than A*. The goal
        is tested when a node is <em>removed</em> from the queue, not when it is first
        discovered: only then is it certain that no cheaper route to it remains.
      </div>
    </div>
  )
}
