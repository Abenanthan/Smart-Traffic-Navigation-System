// Transport only: routing and traffic decisions are made by the Python backend.
async function request(path, body, signal) {
  const response = await fetch(`/api/real-map/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  let data
  try { data = await response.json() } catch {
    throw new Error('The map service returned an unreadable response. Check the backend and retry.')
  }
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'The map request could not be completed. Check your selections and retry.')
  }
  return data
}

export const getNetwork = (signal) => request('network', undefined, signal)
export const findRoute = (source, destination) => request('route', { source, destination })
export const updateTraffic = (roadId, traffic) => request('traffic', { roadId, traffic })
export const simulate = () => request('simulate', { allowBlocking: false })
export const reset = () => request('reset', {})
