/**
 * Smart Traffic Navigation System -- dashboard shell.
 *
 * This component holds interface state (what is selected, what is being shown)
 * and nothing else. Every routing and rerouting decision is made by the Python
 * modules and arrives here already decided.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import * as api from './api'
import NetworkGraph from './components/NetworkGraph'
import RerouteBanner, { Recalculating } from './components/RerouteBanner'
import RouteInfoPanel from './components/RouteInfoPanel'
import RouteInputPanel from './components/RouteInputPanel'
import TrafficControlPanel from './components/TrafficControlPanel'
import UCSVisualizationPanel from './components/UCSVisualizationPanel'

const SIMULATION_INTERVAL_MS = 5000

export default function App() {
  const [locations, setLocations] = useState([])
  const [network, setNetwork] = useState(null)

  const [source, setSource] = useState('A')
  const [destination, setDestination] = useState('K')

  const [selectedRoad, setSelectedRoad] = useState('R18')
  const [level, setLevel] = useState('high')

  const [result, setResult] = useState(null)
  const [search, setSearch] = useState(null)
  const [validation, setValidation] = useState(null)

  const [busy, setBusy] = useState(false)
  const [recalculating, setRecalculating] = useState(false)
  const [autoSimulate, setAutoSimulate] = useState(false)
  const [error, setError] = useState(null)
  const [searchState, setSearchState] = useState(null)

  const busyRef = useRef(false)

  // -- initial load -------------------------------------------------------

  useEffect(() => {
    Promise.all([api.getLocations(), api.getNetwork()])
      .then(([locationData, networkData]) => {
        setLocations(locationData.locations)
        setNetwork(networkData)
      })
      .catch((problem) =>
        setError(
          `Could not reach the routing engine (${problem.message}). `
          + 'Start the backend with: uvicorn app.api:app --port 8000',
        ),
      )
  }, [])

  // -- applying a response ------------------------------------------------

  const applyResponse = useCallback((response) => {
    setNetwork(response.network)
    setResult(response.result)
    setValidation(response.result?.validation ?? null)
    setSearch(response.result?.search ?? null)
    setError(null)
  }, [])

  // -- actions ------------------------------------------------------------

  const handleFindRoute = async () => {
    setBusy(true)
    busyRef.current = true
    try {
      applyResponse(await api.findRoute(source, destination))
    } catch (problem) {
      setError(problem.message)
    } finally {
      setBusy(false)
      busyRef.current = false
    }
  }

  const handleUpdateTraffic = async () => {
    setBusy(true)
    busyRef.current = true
    setRecalculating(true)
    try {
      // A brief pause so the "recalculating" state is legible during a demo;
      // the search itself takes well under a millisecond.
      const [response] = await Promise.all([
        api.updateTraffic(selectedRoad, level),
        new Promise((resolve) => setTimeout(resolve, 550)),
      ])
      applyResponse(response)
    } catch (problem) {
      setError(problem.message)
    } finally {
      setRecalculating(false)
      setBusy(false)
      busyRef.current = false
    }
  }

  const handleReset = async () => {
    setBusy(true)
    busyRef.current = true
    try {
      const response = await api.resetTraffic()
      setNetwork(response.network)
      if (response.result) {
        setResult(response.result)
        setSearch(response.result.search)
      }
      setError(null)
    } catch (problem) {
      setError(problem.message)
    } finally {
      setBusy(false)
      busyRef.current = false
    }
  }

  const handleSwap = () => {
    setSource(destination)
    setDestination(source)
  }

  // -- optional automatic traffic simulation ------------------------------

  useEffect(() => {
    if (!autoSimulate) return undefined

    const timer = setInterval(async () => {
      if (busyRef.current) return
      busyRef.current = true
      setRecalculating(true)
      try {
        const [response] = await Promise.all([
          api.simulateStep(false),
          new Promise((resolve) => setTimeout(resolve, 450)),
        ])
        applyResponse(response)
      } catch (problem) {
        setError(problem.message)
        setAutoSimulate(false)
      } finally {
        setRecalculating(false)
        busyRef.current = false
      }
    }, SIMULATION_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [autoSimulate, applyResponse])

  // -- render -------------------------------------------------------------

  if (!network) {
    return (
      <div className="app">
        <header className="header">
          <div>
            <h1>Smart Traffic Navigation System</h1>
            <p className="subtitle">Uniform Cost Search over a weighted road graph</p>
          </div>
        </header>
        <div style={{ padding: 24 }}>
          {error ? (
            <div className="message error">{error}</div>
          ) : (
            <div className="empty-state">Loading the road network…</div>
          )}
        </div>
      </div>
    )
  }

  const activeRoute = result?.route ?? network.activeRoute ?? null

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Smart Traffic Navigation System</h1>
          <p className="subtitle">
            Least-cost route selection by Uniform Cost Search, with dynamic rerouting
          </p>
        </div>

        <div className="header-flow">
          <span>road network</span>
          <span className="arrow">+</span>
          <span>traffic</span>
          <span className="arrow">→</span>
          <span>weighted graph</span>
          <span className="arrow">→</span>
          <span>UCS</span>
          <span className="arrow">→</span>
          <span>least-cost route</span>
        </div>

        <span className="simulated-badge">● Simulated traffic data</span>
      </header>

      <div className="layout">
        {/* ------------------------------------------------ left column */}
        <div className="col">
          <RouteInputPanel
            locations={locations}
            source={source}
            destination={destination}
            onSourceChange={setSource}
            onDestinationChange={setDestination}
            onFindRoute={handleFindRoute}
            onSwap={handleSwap}
            busy={busy}
            validation={validation}
          />

          <TrafficControlPanel
            roads={network.roads}
            nodes={network.nodes}
            selectedRoad={selectedRoad}
            onSelectRoad={setSelectedRoad}
            level={level}
            onLevelChange={setLevel}
            onApply={handleUpdateTraffic}
            onReset={handleReset}
            busy={busy}
            autoSimulate={autoSimulate}
            onAutoSimulateChange={setAutoSimulate}
          />
        </div>

        {/* ---------------------------------------------- centre column */}
        <div className="col">
          {error && <div className="message error">{error}</div>}
          {recalculating ? <Recalculating /> : <RerouteBanner result={result} />}

          <div className="panel">
            <div className="panel-head">
              <h2>Road network</h2>
              <span className="module-tag">Modules 2 &amp; 4 · Weighted graph</span>
            </div>
            <NetworkGraph
              nodes={network.nodes}
              roads={network.roads}
              route={activeRoute}
              source={source}
              destination={destination}
              selectedRoad={selectedRoad}
              onSelectRoad={setSelectedRoad}
              searchState={searchState}
            />
          </div>
        </div>

        {/* ----------------------------------------------- right column */}
        <div className="col col-right">
          <RouteInfoPanel route={activeRoute} />
          <UCSVisualizationPanel search={search} onStepChange={setSearchState} />
        </div>
      </div>

      <footer className="footer">
        Foundations of Artificial Intelligence — academic project. Traffic conditions are
        simulated; the system does not consume live traffic data.
        <br />
        Edge cost = base travel time + traffic delay (low +0, medium +5, high +12 minutes;
        blocked roads are excluded from the graph).
      </footer>
    </div>
  )
}
