import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../realMapApi'
import ThemeToggle from '../components/ThemeToggle'
import RerouteBanner from '../components/RerouteBanner'
import GeographicMap from '../components/RealMap/GeographicMap'
import './real-map.css'

const LEVELS = [['low', 'Low', '+0 min'], ['medium', 'Medium', '+5 min'], ['high', 'High', '+12 min'], ['blocked', 'Blocked', 'Unavailable']]

export default function RealMapNavigationPage() {
  const [network, setNetwork] = useState(null)
  const [source, setSource] = useState('')
  const [destination, setDestination] = useState('')
  const [roadId, setRoadId] = useState('')
  const [level, setLevel] = useState('high')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [auto, setAuto] = useState(false)
  const [pickMode, setPickMode] = useState(null)
  const [fitVersion, setFitVersion] = useState(0)
  const [reload, setReload] = useState(0)
  const [updatedAt, setUpdatedAt] = useState(null)
  const lock = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    setError('')
    api.getNetwork(controller.signal).then(data => {
      setNetwork(data)
      const pair = data.requestedPair
      setSource(pair?.[0] ?? data.defaults.source)
      setDestination(pair?.[1] ?? data.defaults.destination)
      setRoadId(data.activeRoute?.roadIds?.[0] ?? data.roads[0]?.roadId ?? '')
      setResult(data.lastResult)
    }).catch(problem => {
      if (problem.name !== 'AbortError') setError(`Could not load the road network. ${problem.message}`)
    })
    return () => controller.abort()
  }, [reload])

  const apply = useCallback(response => {
    setNetwork(response.network)
    setResult(response.result)
    setError('')
    if (response.result?.trafficUpdate) setUpdatedAt(new Date())
  }, [])

  const run = useCallback(async (label, action) => {
    if (lock.current) return
    lock.current = true
    setBusy(label)
    setError('')
    try {
      const response = await action()
      apply(response)
      return response
    } catch (problem) {
      setError(problem.message || 'The map service is unavailable. Check the backend and retry.')
      setAuto(false)
    } finally {
      lock.current = false
      setBusy('')
    }
  }, [apply])

  useEffect(() => {
    if (!auto) return undefined
    const timer = setInterval(() => run('Updating traffic and running UCS…', api.simulate), 5000)
    return () => clearInterval(timer)
  }, [auto, run])

  function selectLocation(which, id) {
    if (lock.current) return
    if (which === 'source') setSource(id)
    else setDestination(id)
    setPickMode(null)
    setAuto(false)
    setError('')
  }

  async function findRoute(event) {
    event.preventDefault()
    setPickMode(null)
    const response = await run('Finding the optimal route with UCS…', () => api.findRoute(source, destination))
    if (response?.result?.route) {
      setRoadId(response.result.route.roadIds[0])
      setFitVersion(v => v + 1)
    }
  }

  const selectedRoad = network?.roads.find(road => road.roadId === roadId)
  const pendingLocations = network?.requestedPair && (network.requestedPair[0] !== source || network.requestedPair[1] !== destination)
  const route = !pendingLocations ? network?.activeRoute : null
  const nameOf = id => network?.locations.find(node => node.id === id)?.name ?? id

  return (
    <div className="real-map-page">
      <header className="header">
        <div>
          <h1>Real map navigation</h1>
          <p className="subtitle">Besant Nagar, Chennai · Real roads. Your UCS engine.</p>
        </div>
        <div className="header-actions">
          <span className="simulated-badge">● Simulated Real-Time Traffic</span>
          <ThemeToggle />
        </div>
      </header>

      {!network ? (
        <main className="rm-loading">
          {error ? <div className="message error" role="alert">{error}<br /><button className="ghost small" onClick={() => setReload(n => n + 1)}>Retry loading map</button></div>
            : <div className="empty-state" role="status">Loading the saved OpenStreetMap road network…</div>}
        </main>
      ) : (
        <main className="rm-layout">
          <aside className="rm-sidebar" aria-label="Route and traffic controls">
            <section className="panel">
              <div className="panel-head"><h2>Where are you heading?</h2></div>
              <form className="panel-body" onSubmit={findRoute}>
                <p className="panel-intro">Choose a road junction in the supported area, or pick one on the map.</p>
                {[['source', 'From', source], ['destination', 'To', destination]].map(([which, label, value]) => (
                  <div className="field" key={which}>
                    <div className="rm-field-heading">
                      <label htmlFor={`rm-${which}`}><span className={`rm-stop ${which}`}>{which === 'source' ? 'A' : 'B'}</span>{label}</label>
                      <button type="button" className="ghost small" disabled={!!busy} aria-pressed={pickMode === which} onClick={() => setPickMode(current => current === which ? null : which)}>{pickMode === which ? 'Cancel pick' : 'Pick on map'}</button>
                    </div>
                    <select id={`rm-${which}`} value={value} disabled={!!busy} onChange={event => selectLocation(which, event.target.value)}>
                      <option value="">Choose a location…</option>
                      {network.locations.map(location => <option key={location.id} value={location.id}>{location.name}</option>)}
                    </select>
                  </div>
                ))}
                <div className="swap-row"><button type="button" className="ghost small" disabled={!!busy} onClick={() => { setSource(destination); setDestination(source); setAuto(false); setPickMode(null) }}>⇅ Swap locations</button></div>
                <button className="primary" type="submit" disabled={!!busy || !source || !destination}>Find optimal route</button>
                {source && source === destination && <p className="rm-inline-note">Choose different starting and destination junctions.</p>}
                {pendingLocations && <p className="rm-inline-note">Locations changed. Find a route to use these selections.</p>}
              </form>
            </section>

            <section className="panel">
              <div className="panel-head"><h2>Traffic simulation</h2><span className="module-tag">+0 / +5 / +12 min</span></div>
              <div className="panel-body">
                <p className="panel-intro">Click a colored road on the map or choose a segment below.</p>
                <div className="field">
                  <label htmlFor="rm-road">Road segment</label>
                  <select id="rm-road" value={roadId} disabled={!!busy} onChange={event => setRoadId(event.target.value)}>
                    {network.roads.map(road => <option key={road.roadId} value={road.roadId}>{road.roadId} · {road.name}{road.oneWay ? ' (one-way)' : ''}</option>)}
                  </select>
                </div>
                {selectedRoad && <div className="rm-road-detail">
                  <strong>{selectedRoad.name}</strong>
                  <span>{selectedRoad.from} {selectedRoad.oneWay ? '→' : '↔'} {selectedRoad.to} · {(selectedRoad.distance * 1000).toFixed(0)} m</span>
                  <div><span className={`traffic-pill ${selectedRoad.traffic}`}>{selectedRoad.traffic}</span><b>{selectedRoad.traversable ? `${selectedRoad.baseTravelTime} + ${selectedRoad.trafficDelay} = ${selectedRoad.cost} min` : 'Road unavailable'}</b></div>
                </div>}
                <div className="level-picker" role="group" aria-label="New traffic level">
                  {LEVELS.map(([value, label]) => <button key={value} type="button" className={`level-option ${value} ${level === value ? 'selected' : ''}`} aria-pressed={level === value} disabled={!!busy} onClick={() => setLevel(value)}><span className={`dot ${value}`} />{label}</button>)}
                </div>
                <p className="delay-note">{LEVELS.find(item => item[0] === level)[2]}{level === 'blocked' ? ' to routing' : ' traffic delay per road'}</p>
                <button className="primary" type="button" disabled={!!busy || !roadId || !!pendingLocations} onClick={() => run('Updating road costs and rerouting with UCS…', () => api.updateTraffic(roadId, level))}>Apply traffic change</button>
                <div className="button-row rm-secondary-actions">
                  <button type="button" disabled={!!busy || !!pendingLocations} onClick={() => run('Simulating a traffic change…', api.simulate)}>Simulate change</button>
                  <button type="button" className="ghost" disabled={!!busy || !!pendingLocations} onClick={() => { setAuto(false); run('Resetting map traffic…', api.reset) }}>Reset traffic</button>
                </div>
                <div className="toggle-row">
                  <span className="label-text">Auto-simulate<br /><small>One random change every 5 seconds</small></span>
                  <label className="switch"><input type="checkbox" aria-label="Auto-simulate real-map traffic" checked={auto} disabled={!!busy || !!pendingLocations} onChange={event => setAuto(event.target.checked)} /><span className="track" /></label>
                </div>
                <p className="rm-inline-note">{updatedAt ? `Last simulated update: ${updatedAt.toLocaleTimeString()}` : 'All roads start at low traffic. No live traffic feed.'}</p>
              </div>
            </section>
          </aside>

          <div className="rm-content">
            {error && <div className="message error" role="alert">{error}</div>}
            <div aria-live="polite" aria-atomic="true">
              {busy ? <div className="recalculating"><span className="spinner" />{busy}</div>
                : !pendingLocations && result ? <RerouteBanner result={result} /> : null}
            </div>
            <section className="panel rm-map-panel">
              <div className="panel-head"><div><h2>Besant Nagar</h2><p className="rm-map-caption">{network.locations.length} junctions · {network.roads.length} road segments · Bounded demo area</p></div><button type="button" className="ghost small" onClick={() => setFitVersion(v => v + 1)}>{route ? 'Fit route' : 'Fit area'}</button></div>
              {pickMode && <div className="rm-pick-notice" role="status">Click near a road junction to choose your {pickMode === 'source' ? 'starting point' : 'destination'}. Selection snaps to a junction within 80 m.</div>}
              <GeographicMap network={network} route={route} source={source} destination={destination} selectedRoad={roadId} onRoadSelect={setRoadId} pickMode={busy ? null : pickMode} onPick={selectLocation} onPickError={setError} fitVersion={fitVersion} />
              <div className="graph-legend">
                {LEVELS.map(([value, label]) => <span className="legend-item" key={value}><span className={`dot ${value}`} />{label} <span className="rm-count">{network.trafficCounts[value]}</span></span>)}
                <span className="legend-item"><span className="rm-route-swatch" />UCS route</span>
                <span className="rm-map-caption">Drag to pan · + / − to zoom</span>
              </div>
            </section>

            <section className="panel rm-route-panel" aria-label="Real-map route information">
              <div className="panel-head"><h2>Your route</h2><span className="module-tag">Uniform Cost Search</span></div>
              {!route ? <div className="empty-state">{result && !result.success && !pendingLocations ? 'No route to display. Adjust the locations or reopen blocked roads, then try again.' : 'Choose your locations and select Find optimal route to see the least-cost path.'}</div> : <div className="panel-body">
                <div className="rm-route-endpoints"><strong>{nameOf(route.source)}</strong><span aria-hidden="true">→</span><strong>{nameOf(route.destination)}</strong></div>
                <div className="rm-stats">
                  <div><span>Model travel cost</span><strong>{route.totalCost}<small> min</small></strong></div>
                  <div><span>Road distance</span><strong>{route.totalDistance}<small> km</small></strong></div>
                  <div><span>Traffic delay</span><strong>{route.totalDelay}<small> min</small></strong></div>
                  <div><span>High-traffic roads</span><strong>{route.highTrafficRoads}</strong></div>
                </div>
                <p className="rm-route-math">{route.baseTime} min base travel + {route.totalDelay} min simulated delay = <strong>{route.totalCost} min</strong>. UCS explored {route.nodesExplored} junctions.</p>
                <details className="rm-details"><summary>View {route.steps.length} road segments and costs</summary>
                  <div className="table-scroll"><table className="legs" aria-label="Real-map route costs in minutes"><thead><tr><th>Road</th><th>Traffic</th><th className="num">Base</th><th className="num">Delay</th><th className="num">Total</th></tr></thead><tbody>
                    {route.steps.map(step => <tr key={step.roadId}><td><button className="rm-road-link" type="button" onClick={() => setRoadId(step.roadId)}>{step.name}</button><small>{step.roadId} · {step.from} → {step.to}</small></td><td><span className={`traffic-pill ${step.traffic}`}>{step.traffic}</span></td><td className="num">{step.baseTravelTime}</td><td className="num">+{step.trafficDelay}</td><td className="num total">{step.cumulativeCost}</td></tr>)}
                  </tbody></table></div>
                </details>
              </div>}
            </section>

            <section className="rm-data-note">
              <strong>About this map</strong>
              <p>Road geometry: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors, ODbL</a>. Snapshot: {network.metadata.snapshotDate.slice(0, 10)}. Only highlighted roads inside this area are supported.</p>
              <p>Base cost assumes 30 km/h and rounds each road segment up to a whole minute. These are demonstration costs, not live arrival estimates. One-way roads are respected; turn restrictions are not modeled. Traffic is simulated, and rerouting starts from the original source. No GPS tracking.</p>
            </section>
          </div>
        </main>
      )}
    </div>
  )
}
