import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../realMapApi'
import ThemeToggle from '../components/ThemeToggle'
import RerouteBanner from '../components/RerouteBanner'
import GeographicMap from '../components/RealMap/GeographicMap'
import PlaceSearch from '../components/RealMap/PlaceSearch'
import './real-map.css'

const LEVELS = [['low', 'Low', 'Normal travel time'], ['medium', 'Medium', '1.5× normal travel time'], ['high', 'High', '2.5× normal travel time'], ['blocked', 'Blocked', 'Unavailable']]

const minutes = value => Number(value.toFixed(2))

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
  const [coordinates, setCoordinates] = useState({ source: null, destination: null })
  const [transportMode, setTransportMode] = useState('car')
  const [currentLocation, setCurrentLocation] = useState(null)
  const [focusLocation, setFocusLocation] = useState(0)
  const [areaVersion, setAreaVersion] = useState(0)
  const [selectionChanged, setSelectionChanged] = useState(true)
  const [locationNote, setLocationNote] = useState('')
  const [nearby, setNearby] = useState([])
  const [nearbyStatus, setNearbyStatus] = useState('Use your location or choose a start to see nearby places.')
  const [focusPoint, setFocusPoint] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    setError('')
    api.getNetwork(controller.signal).then(data => {
      setNetwork(data)
      setSource('')
      setDestination('')
      setRoadId(data.activeRoute?.roadIds?.[0] ?? data.roads[0]?.roadId ?? '')
      setResult(null)
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
    setCoordinates(previous => ({ ...previous, [which]: null }))
    setSelectionChanged(true)
    setPickMode(null)
    setAuto(false)
    setError('')
    setLocationNote('')
  }

  function chooseCoordinate(which, coordinate) {
    if (lock.current) return
    const place = { ...coordinate, name: coordinate.name || `${coordinate.latitude.toFixed(5)}, ${coordinate.longitude.toFixed(5)}` }
    setAuto(false)
    setPickMode(null)
    setError('')
    setLocationNote('')
    setSelectionChanged(true)
    setCoordinates(previous => ({ ...previous, [which]: place }))
    if (which === 'source') setSource('')
    else setDestination('')
    setFocusPoint(place)
  }

  const nearbyCenter = currentLocation || coordinates.source
  useEffect(() => {
    setNearby([])
    if (!nearbyCenter) { setNearbyStatus('Use your location or choose a start to see nearby places.'); return }
    const controller = new AbortController()
    setNearbyStatus('Finding places near you…')
    api.nearbyPlaces(nearbyCenter, controller.signal).then(data => {
      if (controller.signal.aborted) return
      setNearby(data.places)
      setNearbyStatus(data.places.length ? 'Nearby areas and destinations · nearest first' : 'No named places nearby. Search by name or pick on the map.')
    }).catch(problem => { if (problem.name !== 'AbortError') setNearbyStatus(problem.message) })
    return () => controller.abort()
  }, [nearbyCenter])

  function useMyLocation() {
    if (lock.current) return
    if (!navigator.geolocation || !window.isSecureContext) {
      setError('Location requires a supported browser on HTTPS or localhost. You can still choose a start on the map.')
      return
    }
    lock.current = true
    setAuto(false)
    setPickMode(null)
    setError('')
    setBusy('Waiting for your browser location permission…')
    navigator.geolocation.getCurrentPosition(position => {
      const point = { latitude: position.coords.latitude, longitude: position.coords.longitude }
      setCurrentLocation({ ...point, accuracy: position.coords.accuracy })
      setFocusLocation(value => value + 1)
      lock.current = false
      setBusy('')
      chooseCoordinate('source', { ...point, name: 'My current location' })
    }, problem => {
      lock.current = false
      setBusy('')
      setError(({ 1: 'Location permission was denied. Allow it in your browser or pick a start on the map.', 2: 'Your location is unavailable. Pick a start on the map or try again.', 3: 'Location detection timed out. Pick a start on the map or try again.' })[problem.code] || 'Could not detect your location. You can pick a start on the map.')
    }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 })
  }

  async function findRoute(event) {
    event.preventDefault()
    setPickMode(null)
    setAuto(false)
    setSelectionChanged(true)
    const response = await run('Loading roads for your trip and finding the UCS route…', () => api.findTrip(coordinates.source, coordinates.destination, transportMode))
    if (response) {
      setFitVersion(v => v + 1)
      setSelectionChanged(false)
      const snaps = response.snappedLocations
      if (snaps?.source && snaps?.destination) setLocationNote(`Start matched ${snaps.source.distanceMetres} m from the selected place; destination ${snaps.destination.distanceMetres} m. Travel to and from the matched road points is not included.`)
      if (response.network.requestedPair) {
        setSource(response.network.requestedPair[0])
        setDestination(response.network.requestedPair[1])
      }
    }
    if (response?.result?.route) {
      setRoadId(response.result.route.roadIds[0])
    }
  }

  const pendingLocations = selectionChanged || (network?.requestedPair && (network.requestedPair[0] !== source || network.requestedPair[1] !== destination))
  const selectedRoad = !pendingLocations && network?.roads.find(road => road.roadId === roadId)
  const route = !pendingLocations ? network?.activeRoute : null
  const nameOf = id => network?.locations.find(node => node.id === id)?.name ?? id
  const profiles = network?.metadata.transportProfiles || {}
  const profile = profiles[transportMode]
  const walking = transportMode === 'walk'

  return (
    <div className="real-map-page">
      <header className="header">
        <div>
          <h1>Real map navigation</h1>
          <p className="subtitle">Search anywhere · Real roads. Your UCS engine.</p>
        </div>
        <div className="header-actions">
          <span className="simulated-badge">● Simulated Real-Time Traffic</span>
          <ThemeToggle />
        </div>
      </header>

      {!network ? (
        <main className="rm-loading">
          {error ? <div className="message error" role="alert">{error}<br /><button className="ghost small" onClick={() => setReload(n => n + 1)}>Retry loading map</button></div>
            : <div className="empty-state" role="status">Preparing your map…</div>}
        </main>
      ) : (
        <main className="rm-layout">
          <aside className="rm-sidebar" aria-label="Route and traffic controls">
            <section className="panel">
              <div className="panel-head"><h2>Where are you heading?</h2></div>
              <form className="panel-body" onSubmit={findRoute}>
                <div className="field">
                  <label htmlFor="rm-mode">Mode of transport</label>
                  <select id="rm-mode" value={transportMode} disabled={!!busy} onChange={event => {
                    setTransportMode(event.target.value); setSelectionChanged(true); setAuto(false); setPickMode(null); setLocationNote(''); setError('')
                  }}>
                    {Object.entries(profiles).map(([id, item]) => <option key={id} value={id}>{item.label}</option>)}
                  </select>
                  <p className="rm-inline-note">{profile?.label}: assumed average {profile?.speedKmh} km/h. {walking ? 'Walking ignores motor-traffic delays. Blocked paths remain unavailable.' : 'Traffic increases travel time on affected roads.'} Changing mode requires a new route.</p>
                </div>
                <p className="panel-intro">Search for your start and destination, use your current location, or pick on the map.</p>
                {[['source', 'From'], ['destination', 'To']].map(([which, label]) => (
                  <div className="field" key={which}>
                    <div className="rm-field-heading">
                      <label htmlFor={`rm-${which}`}><span className={`rm-stop ${which}`}>{which === 'source' ? 'A' : 'B'}</span>{label}</label>
                      <button type="button" className="ghost small" disabled={!!busy} aria-pressed={pickMode === which} onClick={() => setPickMode(current => current === which ? null : which)}>{pickMode === which ? 'Cancel pick' : 'Pick on map'}</button>
                    </div>
                    <PlaceSearch id={`rm-${which}`} selected={coordinates[which]} disabled={!!busy} bias={currentLocation || coordinates.source} onSelect={place => chooseCoordinate(which, place)} onClear={() => selectLocation(which, '')} />
                    {coordinates[which] && <small className="rm-coordinate">{coordinates[which].latitude.toFixed(5)}, {coordinates[which].longitude.toFixed(5)} · selected place</small>}

                  </div>
                ))}
                <div className="swap-row"><button type="button" className="ghost small" disabled={!!busy} onClick={() => { setSource(destination); setDestination(source); setCoordinates(previous => ({ source: previous.destination, destination: previous.source })); setSelectionChanged(true); setAuto(false); setPickMode(null) }}>⇅ Swap locations</button></div>
                <button className="primary" type="submit" disabled={!!busy || !coordinates.source || !coordinates.destination}>Find optimal route</button>
                {coordinates.source && coordinates.destination && coordinates.source.latitude === coordinates.destination.latitude && coordinates.source.longitude === coordinates.destination.longitude && <p className="rm-inline-note">Choose different starting and destination junctions.</p>}
                {pendingLocations && coordinates.source && coordinates.destination && <p className="rm-inline-note">Find a route to load roads for these places.</p>}
              </form>
            </section>

            <section className="panel">
              <div className="panel-head"><h2>{currentLocation ? 'Near your location' : 'Near your start'}</h2></div>
              <div className="panel-body">
                <button type="button" className="ghost small" disabled={!!busy} onClick={useMyLocation}>Use my location</button>
                <p className="rm-inline-note" role="status">{nearbyStatus}</p>
                {!!nearby.length && <ul className="rm-nearby-list">{nearby.map(place => <li key={`${place.name}-${place.latitude}`}><button type="button" disabled={!!busy} onClick={() => chooseCoordinate('destination', place)}><span>{place.name}</span><small>{place.distanceKm.toFixed(1)} km away · Set destination</small></button></li>)}</ul>}
              </div>
            </section>

            <section className="panel">
              <div className="panel-head"><h2>Traffic simulation</h2><span className="module-tag">{walking ? 'Walking: no congestion delay' : '1× / 1.5× / 2.5×'}</span></div>
              <div className="panel-body">
                <p className="panel-intro">Click a colored road on the map or choose a segment below.</p>
                <div className="field">
                  <label htmlFor="rm-road">Road segment</label>
                  <select id="rm-road" value={pendingLocations ? '' : roadId} disabled={!!busy || !!pendingLocations} onChange={event => setRoadId(event.target.value)}>
                    {pendingLocations ? <option value="">Find a route to load roads</option> : network.roads.map(road => <option key={road.roadId} value={road.roadId}>{road.roadId} · {road.name}{road.oneWay ? ' (one-way)' : ''}</option>)}
                  </select>
                </div>
                {selectedRoad && <div className="rm-road-detail">
                  <strong>{selectedRoad.name}</strong>
                  <span>{selectedRoad.from} {selectedRoad.oneWay ? '→' : '↔'} {selectedRoad.to} · {(selectedRoad.distance * 1000).toFixed(0)} m</span>
                  <div><span className={`traffic-pill ${selectedRoad.traffic}`}>{selectedRoad.traffic}</span><b>{selectedRoad.traversable ? `${minutes(selectedRoad.baseTravelTime)} + ${minutes(selectedRoad.trafficDelay)} = ${minutes(selectedRoad.cost)} min` : 'Road unavailable'}</b></div>
                </div>}
                <div className="level-picker" role="group" aria-label="New traffic level">
                  {LEVELS.map(([value, label]) => <button key={value} type="button" className={`level-option ${value} ${level === value ? 'selected' : ''}`} aria-pressed={level === value} disabled={!!busy} onClick={() => setLevel(value)}><span className={`dot ${value}`} />{label}</button>)}
                </div>
                <p className="delay-note">{walking && level !== 'blocked' ? 'No motor-traffic delay added to walking time' : LEVELS.find(item => item[0] === level)[2]}{level === 'blocked' ? ' to routing' : ''}</p>
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
            {locationNote && <p className="rm-location-note" role="status">{locationNote}</p>}
            <div aria-live="polite" aria-atomic="true">
              {busy ? <div className="recalculating"><span className="spinner" />{busy}</div>
                : !pendingLocations && result ? <RerouteBanner result={{ ...result, previousCostNow: result.previousCostNow == null ? null : minutes(result.previousCostNow), saving: result.saving == null ? null : minutes(result.saving), route: result.route ? { ...result.route, totalCost: minutes(result.route.totalCost) } : null }} /> : null}
            </div>
            <section className="panel rm-map-panel">
              <div className="panel-head"><div><h2>OpenStreetMap</h2><p className="rm-map-caption">Search worldwide · Roads load for your selected trip</p></div><button type="button" className="ghost small" onClick={() => setFitVersion(v => v + 1)}>{route ? 'Fit route' : 'Fit area'}</button></div>
              <div className="rm-map-tools">
                <button type="button" className="primary small" disabled={!!busy} onClick={useMyLocation}>Use my location</button>
                <button type="button" className="ghost small" onClick={() => setAreaVersion(value => value + 1)}>Routing area</button>
                <span>{!pendingLocations ? `${network.locations.length} junctions · ${network.roads.length} road segments loaded` : 'Choose two places to load their roads'}</span>
              </div>
              {pickMode && <div className="rm-pick-notice" role="status">Click near a road junction to choose your {pickMode === 'source' ? 'starting point' : 'destination'}. Road matching happens when you find a route.</div>}
              <GeographicMap network={pendingLocations ? { ...network, roads: [] } : network} route={route} source={source} destination={destination} selectedRoad={roadId} onRoadSelect={setRoadId} pickMode={busy ? null : pickMode} onPick={chooseCoordinate} fitVersion={fitVersion} sourceCoordinate={coordinates.source} destinationCoordinate={coordinates.destination} currentLocation={currentLocation} focusLocation={focusLocation} areaVersion={areaVersion} focusPoint={focusPoint} showBounds={!pendingLocations} />
              <div className="graph-legend">
                {LEVELS.map(([value, label]) => <span className="legend-item" key={value}><span className={`dot ${value}`} />{label} <span className="rm-count">{pendingLocations ? '—' : network.trafficCounts[value]}</span></span>)}
                <span className="legend-item"><span className="rm-route-swatch" />UCS route</span>
                <span className="rm-map-caption">Drag to pan · + / − to zoom</span>
              </div>
            </section>

            <section className="panel rm-route-panel" aria-label="Real-map route information">
              <div className="panel-head"><h2>Your route{route ? ` · ${profiles[route.transportMode]?.label || ''}` : ''}</h2><span className="module-tag">Uniform Cost Search</span></div>
              {!route ? <div className="empty-state">{result && !result.success && !pendingLocations ? 'No route to display. Adjust the locations or reopen blocked roads, then try again.' : 'Choose your locations and select Find optimal route to see the least-cost path.'}</div> : <div className="panel-body">
                <div className="rm-route-endpoints"><strong>{coordinates.source?.name || nameOf(route.source)}</strong><span aria-hidden="true">→</span><strong>{coordinates.destination?.name || nameOf(route.destination)}</strong></div>
                <div className="rm-stats">
                  <div><span>Approx. travel time</span><strong>{minutes(route.totalCost)}<small> min</small></strong></div>
                  <div><span>Road distance</span><strong>{route.totalDistance}<small> km</small></strong></div>
                  <div><span>Traffic delay</span><strong>{minutes(route.totalDelay)}<small> min</small></strong></div>
                  <div><span>High-traffic roads</span><strong>{route.highTrafficRoads}</strong></div>
                </div>
                <p className="rm-route-math">{minutes(route.baseTime)} min base travel + {minutes(route.totalDelay)} min simulated delay = <strong>{minutes(route.totalCost)} min</strong>. UCS explored {route.nodesExplored} junctions.</p>
                <details className="rm-details"><summary>View {route.steps.length} road segments and costs</summary>
                  <div className="table-scroll"><table className="legs" aria-label="Real-map route costs in minutes"><thead><tr><th>Road</th><th>Traffic</th><th className="num">Base</th><th className="num">Delay</th><th className="num">Total</th></tr></thead><tbody>
                    {route.steps.map(step => <tr key={step.roadId}><td><button className="rm-road-link" type="button" onClick={() => setRoadId(step.roadId)}>{step.name}</button><small>{step.roadId} · {step.from} → {step.to}</small></td><td><span className={`traffic-pill ${step.traffic}`}>{step.traffic}</span></td><td className="num">{minutes(step.baseTravelTime)}</td><td className="num">+{minutes(step.trafficDelay)}</td><td className="num total">{minutes(step.cumulativeCost)}</td></tr>)}
                  </tbody></table></div>
                </details>
              </div>}
            </section>

            <section className="rm-data-note">
              <strong>About this map</strong>
              <p>Road geometry: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors, ODbL</a>. Place search: Photon. { !pendingLocations && <>Road data: {network.metadata.snapshotDate.slice(0, 10)}.</>} Routing uses the highlighted roads loaded around this trip. Shorter trips work best; loading is limited to 100 km straight-line, 2,500 km², and 15,000 junctions.</p>
              <p>Approximate time uses distance and the selected mode's assumed speed, without rounding each road segment. For motor vehicles, medium traffic takes 1.5× and high traffic 2.5× the normal time. Walking ignores these delays and uses pedestrian-accessible roads and paths. Signals, stops, terrain and actual speeds can change journey time; this is not a live traffic estimate. Mapped mode-specific access and direction rules are used; turn restrictions and node barriers are not modeled. Rerouting starts from the selected source. One-time location only; no continuous GPS tracking. Loading a new trip starts a new traffic simulation.</p>
            </section>
          </div>
        </main>
      )}
    </div>
  )
}
