import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export default function GeographicMap({ network, route, source, destination, selectedRoad, onRoadSelect, pickMode, onPick, fitVersion, sourceCoordinate, destinationCoordinate, currentLocation, focusLocation, areaVersion, focusPoint, showBounds = true }) {
  const container = useRef(null)
  const map = useRef(null)
  const roadsLayer = useRef(null)
  const routeLayer = useRef(null)
  const markersLayer = useRef(null)
  const locationLayer = useRef(null)
  const boundsLayer = useRef(null)
  const latest = useRef({})
  const [tileError, setTileError] = useState(false)
  const [theme, setTheme] = useState(document.documentElement.dataset.theme)
  latest.current = { network, pickMode, onPick, onRoadSelect }

  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(document.documentElement.dataset.theme))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const view = L.map(container.current, { preferCanvas: true, scrollWheelZoom: true, minZoom: 2, maxZoom: 19, zoomSnap: .25, worldCopyJump: true })
    map.current = view
    view.setView([20, 0], 3)
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>',
    }).addTo(view)
    tiles.on('tileerror', () => setTileError(true))
    boundsLayer.current = L.layerGroup().addTo(view)
    roadsLayer.current = L.layerGroup().addTo(view)
    routeLayer.current = L.layerGroup().addTo(view)
    markersLayer.current = L.layerGroup().addTo(view)
    locationLayer.current = L.layerGroup().addTo(view)
    view.on('click', event => {
      const state = latest.current
      if (!state.pickMode) return
      const point = event.latlng.wrap()
      state.onPick(state.pickMode, { latitude: point.lat, longitude: point.lng })
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
    boundsLayer.current?.clearLayers()
    if (!showBounds || !boundsLayer.current) return
    const [s, w, n, e] = network.metadata.bbox
    L.rectangle([[s, w], [n, e]], { color: '#8A7254', weight: 1, fill: false, dashArray: '5 6', interactive: false }).addTo(boundsLayer.current)
  }, [network.metadata, showBounds])

  useEffect(() => {
    if (focusPoint && map.current) map.current.setView([focusPoint.latitude, focusPoint.longitude], 15, { animate: false })
  }, [focusPoint])

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
    for (const [id, label, color, coordinate] of [[source, 'From', '#2463A0', sourceCoordinate], [destination, 'To', '#C81B33', destinationCoordinate]]) {
      const location = network.locations.find(node => node.id === id)
      if (!location && !coordinate) continue
      const point = coordinate ? [coordinate.latitude, coordinate.longitude] : location.coordinates
      const name = coordinate ? `${point[0].toFixed(5)}, ${point[1].toFixed(5)}` : location.name
      const icon = L.divIcon({
        className: 'rm-map-marker',
        html: `<span style="background:${color}">${label === 'From' ? 'A' : 'B'}</span>`,
        iconSize: [30, 30], iconAnchor: [15, 15],
      })
      const marker = L.marker(point, { icon, title: `${label}: ${name}`, alt: `${label}: ${name}` }).addTo(markersLayer.current)
      marker.on('click', () => {
        if (latest.current.pickMode) latest.current.onPick(latest.current.pickMode, { latitude: point[0], longitude: point[1] })
      })
      const content = document.createElement('span')
      content.textContent = `${label}: ${name}${coordinate && location ? ` · Road junction: ${location.name}` : ''}`
      marker.bindPopup(content)
    }
  }, [network.locations, source, destination, route, theme, sourceCoordinate, destinationCoordinate])

  useEffect(() => {
    if (!locationLayer.current) return
    locationLayer.current.clearLayers()
    if (!currentLocation) return
    const point = [currentLocation.latitude, currentLocation.longitude]
    L.circle(point, { radius: currentLocation.accuracy, color: '#2563EB', weight: 1, fillOpacity: .1, interactive: false }).addTo(locationLayer.current)
    const icon = L.divIcon({ className: 'rm-current-marker', html: '<span></span>', iconSize: [18, 18], iconAnchor: [9, 9] })
    L.marker(point, { icon, title: 'You are here', alt: 'You are here' }).bindPopup('You are here · One-time device location').addTo(locationLayer.current)
  }, [currentLocation])

  useEffect(() => {
    if (map.current && currentLocation) map.current.setView([currentLocation.latitude, currentLocation.longitude], 16, { animate: false })
  }, [currentLocation, focusLocation])

  useEffect(() => {
    if (!map.current || !showBounds) return
    const [s, w, n, e] = network.metadata.bbox
    map.current.fitBounds([[s, w], [n, e]], { padding: [24, 24], animate: false })
  }, [areaVersion])

  useEffect(() => {
    if (!map.current || !showBounds) return
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
        <div ref={container} className="rm-map" aria-label="Interactive world map with selected places, loaded OpenStreetMap roads and the UCS route" />
      </div>
    </>
  )
}
