import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export default function GeographicMap({ network, route, source, destination, selectedRoad, onRoadSelect, pickMode, onPick, onPickError, fitVersion }) {
  const container = useRef(null)
  const map = useRef(null)
  const roadsLayer = useRef(null)
  const routeLayer = useRef(null)
  const markersLayer = useRef(null)
  const latest = useRef({})
  const [tileError, setTileError] = useState(false)
  const [theme, setTheme] = useState(document.documentElement.dataset.theme)
  latest.current = { network, pickMode, onPick, onPickError, onRoadSelect }

  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(document.documentElement.dataset.theme))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const view = L.map(container.current, { scrollWheelZoom: false, minZoom: 13, maxZoom: 19, zoomSnap: .25 })
    map.current = view
    const [s, w, n, e] = latest.current.network.metadata.bbox
    const bounds = L.latLngBounds([s, w], [n, e])
    view.fitBounds(bounds, { padding: [16, 16] })
    view.setMaxBounds(bounds.pad(.5))
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>',
    }).addTo(view)
    tiles.on('tileerror', () => setTileError(true))
    L.rectangle(bounds, { color: '#8A7254', weight: 1, fill: false, dashArray: '5 6', interactive: false }).addTo(view)
    roadsLayer.current = L.layerGroup().addTo(view)
    routeLayer.current = L.layerGroup().addTo(view)
    markersLayer.current = L.layerGroup().addTo(view)
    view.on('click', event => {
      const state = latest.current
      if (!state.pickMode) return
      const closest = state.network.locations.reduce((best, node) => {
        const metres = view.distance(event.latlng, node.coordinates)
        return !best || metres < best.metres ? { node, metres } : best
      }, null)
      if (!closest || closest.metres > 80) {
        state.onPickError('Choose a point within 80 metres of a supported road junction, or use the location list.')
        return
      }
      state.onPick(state.pickMode, closest.node.id)
    })
    const resize = new ResizeObserver(() => view.invalidateSize())
    resize.observe(container.current)
    return () => {
      resize.disconnect()
      view.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    if (!roadsLayer.current) return
    roadsLayer.current.clearLayers()
    const styles = getComputedStyle(document.documentElement)
    const colors = Object.fromEntries(['low', 'medium', 'high', 'blocked'].map(level => [level, styles.getPropertyValue(`--${level}`).trim()]))
    for (const road of network.roads) {
      const line = L.polyline(road.geometry, {
        color: colors[road.traversable ? road.traffic : 'blocked'],
        weight: road.roadId === selectedRoad ? 7 : 3,
        opacity: road.roadId === selectedRoad ? 1 : .8,
        dashArray: road.traversable ? undefined : '5 6',
        bubblingMouseEvents: true,
      }).addTo(roadsLayer.current)
      const tip = document.createElement('span')
      tip.textContent = `${road.name} · ${road.roadId} · ${road.traversable ? `${road.cost} min · ${road.traffic}` : 'Blocked'}${road.oneWay ? ' · One-way' : ''}`
      line.bindTooltip(tip, { sticky: true })
      line.on('click', () => {
        if (!latest.current.pickMode) latest.current.onRoadSelect(road.roadId)
      })
    }
  }, [network.roads, selectedRoad, theme])

  useEffect(() => {
    if (!routeLayer.current) return
    routeLayer.current.clearLayers()
    if (route?.geometry?.length) {
      L.polyline(route.geometry, { color: '#FFFAF3', weight: 9, opacity: .9, interactive: false }).addTo(routeLayer.current)
      L.polyline(route.geometry, { color: '#2463A0', weight: 5, opacity: 1, interactive: false }).addTo(routeLayer.current)
    }
    markersLayer.current.clearLayers()
    for (const [id, label, color] of [[source, 'From', '#2463A0'], [destination, 'To', '#C81B33']]) {
      const location = network.locations.find(node => node.id === id)
      if (!location) continue
      const icon = L.divIcon({
        className: 'rm-map-marker',
        html: `<span style="background:${color}">${label === 'From' ? 'A' : 'B'}</span>`,
        iconSize: [30, 30], iconAnchor: [15, 15],
      })
      const marker = L.marker(location.coordinates, { icon, title: `${label}: ${location.name}`, alt: `${label}: ${location.name}` }).addTo(markersLayer.current)
      marker.on('click', () => {
        if (latest.current.pickMode) latest.current.onPick(latest.current.pickMode, location.id)
      })
      const content = document.createElement('span')
      content.textContent = `${label}: ${location.name}`
      marker.bindPopup(content)
    }
  }, [network.locations, source, destination, route, theme])

  useEffect(() => {
    if (!map.current) return
    const geometry = route?.geometry
    const [s, w, n, e] = network.metadata.bbox
    map.current.fitBounds(geometry?.length ? L.latLngBounds(geometry) : L.latLngBounds([s, w], [n, e]), { padding: [40, 40], maxZoom: 17, animate: false })
  }, [fitVersion]) // Recenter explicitly; traffic refreshes do not interrupt map exploration.

  return (
    <>
      {tileError && <div className="rm-map-warning" role="status">Background tiles could not load. The saved road geometry and UCS routing still work. Check your connection and reload to retry tiles.</div>}
      <div className={pickMode ? 'rm-map-frame rm-picking' : 'rm-map-frame'}>
        {/* Leaflet owns the container's additional classes. Keep React's class
            static so changing pick mode never removes leaflet-container. */}
        <div ref={container} className="rm-map" aria-label="Interactive map of Besant Nagar with OpenStreetMap roads and the UCS route" />
      </div>
    </>
  )
}
