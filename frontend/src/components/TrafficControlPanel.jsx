/**
 * TRAFFIC AREA -- Module 3, Traffic Data.
 *
 * Choose a road, choose a traffic level, apply it. The delay each level adds is
 * shown next to it, so the effect on the edge cost is visible before the change
 * is made.
 *
 * The traffic set here is SIMULATED. Nothing in this panel contacts a live
 * traffic service.
 */

const LEVELS = [
  { value: 'low', label: 'Low', delay: '+0 min' },
  { value: 'medium', label: 'Medium', delay: '+5 min' },
  { value: 'high', label: 'High', delay: '+12 min' },
  { value: 'blocked', label: 'Blocked', delay: 'closed' },
]

export default function TrafficControlPanel({
  roads,
  nodes,
  selectedRoad,
  onSelectRoad,
  level,
  onLevelChange,
  onApply,
  onReset,
  busy,
  autoSimulate,
  onAutoSimulateChange,
}) {
  const nameOf = (id) => nodes.find((node) => node.id === id)?.name ?? id
  const road = roads.find((r) => r.roadId === selectedRoad)

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Traffic conditions</h2>
        <span className="module-tag">Module 3 · Traffic</span>
      </div>

      <div className="panel-body">
        <div className="field">
          <label htmlFor="road-select">Road</label>
          <select
            id="road-select"
            value={selectedRoad}
            onChange={(event) => onSelectRoad(event.target.value)}
          >
            {roads.map((r) => (
              <option key={r.roadId} value={r.roadId}>
                {r.roadId}: {r.from}–{r.to} ({nameOf(r.from)} → {nameOf(r.to)})
              </option>
            ))}
          </select>
          <p className="road-select-hint">You can also click a road on the map.</p>
        </div>

        {road && (
          <div className="current-road-info">
            <div className="row">
              <span>base travel time</span>
              <b>{road.baseTravelTime} min</b>
            </div>
            <div className="row">
              <span>traffic delay</span>
              <b>{road.traversable ? `+${road.trafficDelay} min` : '—'}</b>
            </div>
            <div className="row">
              <span>current cost</span>
              <b style={{ color: road.traversable ? '#38bdf8' : '#f87171' }}>
                {road.traversable ? `${road.cost} min` : 'blocked'}
              </b>
            </div>
          </div>
        )}

        <div className="field" style={{ marginTop: 14 }}>
          <label>Traffic level</label>
          <div className="level-picker">
            {LEVELS.map((option) => (
              <button
                type="button"
                key={option.value}
                className={
                  `level-option ${option.value} ${level === option.value ? 'selected' : ''}`
                }
                onClick={() => onLevelChange(option.value)}
              >
                <span className={`dot ${option.value}`} />
                {option.label}
              </button>
            ))}
          </div>
          <div className="delay-note">
            {LEVELS.find((option) => option.value === level)?.delay} traffic delay
          </div>
        </div>

        <div className="button-row" style={{ marginTop: 12 }}>
          <button type="button" className="primary" onClick={onApply} disabled={busy}>
            Update Traffic
          </button>
          <button
            type="button"
            className="ghost"
            onClick={onReset}
            disabled={busy}
            style={{ flex: '0 0 auto' }}
          >
            Reset
          </button>
        </div>

        <div className="toggle-row">
          <span className="label-text">
            Auto-simulate traffic
            <br />
            <span style={{ fontSize: 11, color: 'var(--text-faint)' }}>
              random change every 5 seconds
            </span>
          </span>
          <label className="switch">
            <input
              type="checkbox"
              checked={autoSimulate}
              onChange={(event) => onAutoSimulateChange(event.target.checked)}
            />
            <span className="track" />
          </label>
        </div>
      </div>
    </div>
  )
}
