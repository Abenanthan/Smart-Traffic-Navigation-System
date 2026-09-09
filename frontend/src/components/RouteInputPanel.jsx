/**
 * INPUT AREA -- Module 1, Input Processing.
 *
 * The dropdowns can only offer locations that exist, so most invalid input is
 * prevented rather than rejected. The remaining checks -- source equal to
 * destination, and no route being possible -- are made by the Python module and
 * its message is shown here.
 */

export default function RouteInputPanel({
  locations,
  source,
  destination,
  onSourceChange,
  onDestinationChange,
  onFindRoute,
  onSwap,
  busy,
  validation,
}) {
  const invalidField = validation && !validation.valid ? validation.field : null

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Plan a route</h2>
        <span className="module-tag">Module 1 · Input</span>
      </div>

      <div className="panel-body">
        <p className="panel-intro">Choose two locations. UCS finds the route with the lowest travel time.</p>
        <div className="field">
          <label htmlFor="source-select">Starting location</label>
          <select
            id="source-select"
            className={invalidField === 'source' ? 'invalid' : ''}
            value={source}
            onChange={(event) => onSourceChange(event.target.value)}
          >
            <option value="">Select a starting location…</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.id} — {location.name}
              </option>
            ))}
          </select>
        </div>

        <div className="swap-row">
          <button
            type="button"
            className="ghost small"
            onClick={onSwap}
            disabled={!source && !destination}
            title="Swap source and destination"
          >
            ⇅ Swap
          </button>
        </div>

        <div className="field">
          <label htmlFor="destination-select">Destination</label>
          <select
            id="destination-select"
            className={invalidField === 'destination' ? 'invalid' : ''}
            value={destination}
            onChange={(event) => onDestinationChange(event.target.value)}
          >
            <option value="">Select a destination…</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.id} — {location.name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <button
            type="button"
            className="primary"
            onClick={onFindRoute}
            disabled={busy || !source || !destination}
          >
            {busy ? 'Searching…' : 'Find best route'}
          </button>
        </div>

        {validation && !validation.valid && (
          <div className="message error">{validation.message}</div>
        )}
      </div>
    </div>
  )
}
