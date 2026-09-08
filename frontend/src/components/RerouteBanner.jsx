/**
 * REROUTING NOTIFICATION -- the visible half of Module 6's decision.
 *
 * While the recalculation is in flight the panel says so; when it returns, the
 * decision is shown along with the comparison that produced it: what the route
 * being followed would now cost against what the new route costs.
 */

const STYLES = {
  initial_route:        { css: 'same',    icon: '✓', title: 'Optimal route found' },
  unchanged:            { css: 'same',    icon: '✓', title: 'Route unchanged' },
  cheaper_route_found:  { css: 'updated', icon: '↻', title: 'Route Updated' },
  route_blocked:        { css: 'blocked', icon: '⚠', title: 'Route Updated' },
  no_route:             { css: 'none',    icon: '✕', title: 'No route available' },
}

export function Recalculating() {
  return (
    <div className="recalculating">
      <span className="spinner" />
      Traffic condition changed — recalculating route…
    </div>
  )
}

export default function RerouteBanner({ result }) {
  if (!result) return null

  const style = STYLES[result.decision] ?? STYLES.unchanged
  const showComparison =
    result.decision === 'cheaper_route_found'
    && result.previousCostNow != null
    && result.route

  return (
    <div className={`banner ${style.css}`}>
      <span className="banner-icon">{style.icon}</span>
      <div className="banner-body">
        <div className="banner-title">{result.headline || style.title}</div>
        <div className="banner-text">{result.reason}</div>

        {showComparison && (
          <div className="banner-compare">
            <span className="was">{result.previousCostNow} min</span>
            <span>→</span>
            <span className="now">{result.route.totalCost} min</span>
            {result.saving > 0 && (
              <span className="saving">saving {result.saving} min</span>
            )}
          </div>
        )}

        {result.decision === 'route_blocked' && result.previousRoute && (
          <div className="banner-compare">
            <span className="was">{result.previousRoute.path.join(' → ')}</span>
            <span>→</span>
            <span className="now">{result.route.path.join(' → ')}</span>
          </div>
        )}
      </div>
    </div>
  )
}
