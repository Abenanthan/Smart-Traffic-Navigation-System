/**
 * ROAD NETWORK AREA -- the weighted graph, drawn.
 *
 * Roads are coloured by traffic level and labelled with their current cost, so
 * the number UCS actually adds up is visible on every edge. The chosen route is
 * drawn over the top. While the UCS panel is stepping through the search, the
 * node being expanded and the nodes already explored are marked as well, which
 * is what connects the algorithm trace to the map.
 */

const VIEW_W = 900
const VIEW_H = 600

// Location names are drawn centred under their node, so the horizontal margin
// has to leave room for the longest of them ("Island Fishing Village") rather
// than just for the circle itself.
const PAD_X = 84
const PAD_Y = 44

const TRAFFIC_COLOUR = {
  low: '#34d399',
  medium: '#fbbf24',
  high: '#f87171',
  blocked: '#64748b',
}

export default function NetworkGraph({
  nodes,
  roads,
  route,
  source,
  destination,
  selectedRoad,
  onSelectRoad,
  searchState,
}) {
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))

  // Fit the stored coordinates to the viewport with a margin, so the layout
  // survives changes to the data file.
  const xs = nodes.map((n) => n.x)
  const ys = nodes.map((n) => n.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const scaleX = (VIEW_W - PAD_X * 2) / Math.max(1, maxX - minX)
  const scaleY = (VIEW_H - PAD_Y * 2) / Math.max(1, maxY - minY)

  const px = (n) => PAD_X + (n.x - minX) * scaleX
  const py = (n) => PAD_Y + (n.y - minY) * scaleY

  const routePath = route?.path ?? []
  const routeRoads = new Set(route?.roadIds ?? [])

  const explored = new Set(searchState?.explored ?? [])
  const currentNode = searchState?.node ?? null
  const frontierCosts = Object.fromEntries(
    (searchState?.frontier ?? []).filter((e) => !e.stale).map((e) => [e.node, e.cost]),
  )

  return (
    <div>
      <div className="graph-wrap">
        <svg
          className="graph-svg"
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          role="img"
          aria-label="Road network with current traffic costs"
        >
          <defs>
            <marker
              id="route-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
            </marker>
          </defs>

          {/* ---- roads ---- */}
          <g>
            {roads.map((road) => {
              const a = byId[road.from]
              const b = byId[road.to]
              if (!a || !b) return null

              const x1 = px(a)
              const y1 = py(a)
              const x2 = px(b)
              const y2 = py(b)

              const onRoute = routeRoads.has(road.roadId)
              const isSelected = road.roadId === selectedRoad
              const colour = road.traversable
                ? TRAFFIC_COLOUR[road.traffic]
                : TRAFFIC_COLOUR.blocked

              return (
                <g key={road.roadId}>
                  {/* a wide invisible line, so the road is easy to click */}
                  <line
                    className="road-hit"
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke="transparent"
                    strokeWidth="16"
                    onClick={() => onSelectRoad(road.roadId)}
                  >
                    <title>
                      {`${road.roadId}: ${road.from}-${road.to} — `
                        + (road.traversable
                          ? `${road.baseTravelTime} base + ${road.trafficDelay} delay = ${road.cost} min (${road.traffic})`
                          : 'blocked')}
                    </title>
                  </line>

                  <line
                    className="road-line"
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke={colour}
                    strokeWidth={isSelected ? 4.5 : onRoute ? 3 : 2}
                    strokeDasharray={road.traversable ? undefined : '7 5'}
                    opacity={road.traversable ? (onRoute ? 0.95 : 0.5) : 0.55}
                    onClick={() => onSelectRoad(road.roadId)}
                  />
                </g>
              )
            })}
          </g>

          {/* ---- the chosen route, drawn over the roads ---- */}
          {routePath.length > 1 && (
            <g>
              {routePath.slice(0, -1).map((from, index) => {
                const to = routePath[index + 1]
                const a = byId[from]
                const b = byId[to]
                if (!a || !b) return null
                return (
                  <line
                    key={`${from}-${to}`}
                    x1={px(a)} y1={py(a)} x2={px(b)} y2={py(b)}
                    stroke="#38bdf8"
                    strokeWidth="6"
                    strokeLinecap="round"
                    opacity="0.32"
                  />
                )
              })}
            </g>
          )}

          {/* ---- edge cost labels ---- */}
          <g>
            {roads.map((road) => {
              const a = byId[road.from]
              const b = byId[road.to]
              if (!a || !b) return null

              const mx = (px(a) + px(b)) / 2
              const my = (py(a) + py(b)) / 2
              const onRoute = routeRoads.has(road.roadId)
              const label = road.traversable ? String(road.cost) : '×'

              return (
                <g key={`w-${road.roadId}`} pointerEvents="none">
                  <rect
                    x={mx - (label.length > 1 ? 12 : 9)}
                    y={my - 9}
                    width={label.length > 1 ? 24 : 18}
                    height={18}
                    rx="5"
                    fill="#0a1018"
                    stroke={onRoute ? '#38bdf8' : '#2a3547'}
                    strokeWidth={onRoute ? 1.4 : 1}
                    opacity="0.96"
                  />
                  <text
                    className="edge-weight"
                    x={mx}
                    y={my + 0.5}
                    fill={
                      !road.traversable
                        ? '#94a3b8'
                        : onRoute
                          ? '#7dd3fc'
                          : TRAFFIC_COLOUR[road.traffic]
                    }
                  >
                    {label}
                  </text>
                </g>
              )
            })}
          </g>

          {/* ---- locations ---- */}
          <g>
            {nodes.map((node) => {
              const x = px(node)
              const y = py(node)

              const isSource = node.id === source
              const isDestination = node.id === destination
              const onRoute = routePath.includes(node.id)
              const isCurrent = node.id === currentNode
              const wasExplored = explored.has(node.id)
              const inFrontier = node.id in frontierCosts

              let fill = '#1c2637'
              let stroke = '#2a3547'
              let radius = 13

              if (wasExplored) { fill = '#1e3a4d'; stroke = '#38bdf877' }
              if (inFrontier) { fill = '#2a2416'; stroke = '#fbbf2499' }
              if (onRoute) { fill = '#0c4a6e'; stroke = '#38bdf8'; radius = 14 }
              if (isSource || isDestination) { fill = '#075985'; stroke = '#7dd3fc'; radius = 16 }
              if (isCurrent) { fill = '#0ea5e9'; stroke = '#e0f2fe'; radius = 17 }

              return (
                <g key={node.id}>
                  {isCurrent && (
                    <circle cx={x} cy={y} r={radius + 6} fill="none"
                            stroke="#38bdf8" strokeWidth="1.5" opacity="0.5" />
                  )}
                  <circle
                    className="node-circle"
                    cx={x} cy={y} r={radius}
                    fill={fill} stroke={stroke} strokeWidth="2"
                  />
                  <text
                    className="node-id"
                    x={x} y={y}
                    fill={isCurrent || isSource || isDestination ? '#f0f9ff' : '#cbd5e1'}
                  >
                    {node.id}
                  </text>
                  <text className="node-label" x={x} y={y + radius + 13}>
                    {node.name}
                  </text>
                  {inFrontier && (
                    <text
                      className="edge-weight"
                      x={x + radius + 12}
                      y={y - radius - 2}
                      fill="#fbbf24"
                    >
                      {frontierCosts[node.id]}
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      <div className="graph-legend">
        {['low', 'medium', 'high'].map((level) => (
          <span className="legend-item" key={level}>
            <span className="legend-swatch" style={{ background: TRAFFIC_COLOUR[level] }} />
            {level} traffic
          </span>
        ))}
        <span className="legend-item">
          <span
            className="legend-swatch"
            style={{
              background: 'repeating-linear-gradient(90deg,#64748b 0 4px,transparent 4px 7px)',
            }}
          />
          blocked
        </span>
        <span className="legend-item">
          <span
            className="legend-swatch"
            style={{ background: '#38bdf8', height: 5, opacity: 0.5 }}
          />
          selected route
        </span>
        <span className="legend-item" style={{ marginLeft: 'auto' }}>
          Numbers on roads are current costs in minutes. Click a road to change its traffic.
        </span>
      </div>
    </div>
  )
}
