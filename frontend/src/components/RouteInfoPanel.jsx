/**
 * ROUTE INFORMATION -- Module 6, Optimal Navigation.
 *
 * The route, its cost, and the arithmetic behind that cost leg by leg, so the
 * total can be checked by hand against the numbers drawn on the map.
 */

export default function RouteInfoPanel({ route }) {
  if (!route) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h2>Route information</h2>
          <span className="module-tag">Module 6 · Navigation</span>
        </div>
        <div className="empty-state">
          No route selected yet.
          <br />
          Choose a source and a destination, then select <strong>Find Best Route</strong>.
        </div>
      </div>
    )
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Route information</h2>
        <span className="module-tag">Module 6 · Navigation</span>
      </div>

      <div className="panel-body">
        <div className="stat-grid">
          <div className="stat">
            <div className="stat-label">Total cost</div>
            <div className="stat-value accent">
              {route.totalCost} <span className="stat-unit">min</span>
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Distance</div>
            <div className="stat-value">
              {route.totalDistance} <span className="stat-unit">km</span>
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Traffic delay</div>
            <div className="stat-value">
              {route.totalDelay} <span className="stat-unit">of {route.totalCost} min</span>
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Locations explored</div>
            <div className="stat-value">
              {route.nodesExplored} <span className="stat-unit">by UCS</span>
            </div>
          </div>
        </div>

        <div className="route-chain">
          {route.path.map((node, index) => (
            <span key={`${node}-${index}`} style={{ display: 'contents' }}>
              {index > 0 && <span className="chain-arrow">→</span>}
              <span
                className={
                  `chain-node ${index === 0 || index === route.path.length - 1 ? 'endpoint' : ''}`
                }
              >
                {node}
              </span>
            </span>
          ))}
        </div>

        <div className="route-names">
          {route.pathNames.join(' → ')}
        </div>

        <table className="legs">
          <thead>
            <tr>
              <th>Leg</th>
              <th>Road</th>
              <th>Traffic</th>
              <th className="num">Base</th>
              <th className="num">Delay</th>
              <th className="num">Cost</th>
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {route.steps.map((step) => (
              <tr key={step.roadId}>
                <td>{step.from}→{step.to}</td>
                <td>{step.roadId}</td>
                <td>
                  <span className={`traffic-pill ${step.traffic}`}>{step.traffic}</span>
                </td>
                <td className="num">{step.baseTravelTime}</td>
                <td className="num">+{step.trafficDelay}</td>
                <td className="num">{step.cost}</td>
                <td className="num total">{step.cumulativeCost}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="cost-formula">
          {route.baseTime} min base travel + {route.totalDelay} min traffic delay ={' '}
          <strong>{route.totalCost} min</strong>
        </div>
      </div>
    </div>
  )
}
