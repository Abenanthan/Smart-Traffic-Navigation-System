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
export const resolveCoordinate = (coordinate, role) => request('resolve', { ...coordinate, role })
export const searchPlaces = (query, bias, signal) => request('search', { query, bias }, signal)
export const nearbyPlaces = (coordinate, signal) => request('nearby', coordinate, signal)
export async function findTrip(source, destination, transportMode = 'car') {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 65000)
  try {
    return await request('trip', { source, destination, transportMode }, controller.signal)
  } catch (error) {
    if (controller.signal.aborted) throw new Error('Route loading took too long. Please retry in a moment; your selected places are kept.')
    throw error
  } finally {
    clearTimeout(timeout)
  }
}
