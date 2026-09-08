/**
 * The only place the dashboard talks to the Python backend.
 *
 * Every routing and rerouting decision is made in Python, in the six modules of
 * the system. This file transports answers; it does not compute them.
 */

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body.detail) detail = body.detail
    } catch {
      // response had no JSON body; the status text will do
    }
    throw new Error(detail)
  }

  return response.json()
}

export const getNetwork = () => request('/api/network')

export const getLocations = () => request('/api/locations')

export const findRoute = (source, destination) =>
  request('/api/route', {
    method: 'POST',
    body: JSON.stringify({ source, destination }),
  })

export const updateTraffic = (roadId, traffic) =>
  request('/api/traffic', {
    method: 'POST',
    body: JSON.stringify({ roadId, traffic }),
  })

export const simulateStep = (allowBlocking = false) =>
  request('/api/simulate', {
    method: 'POST',
    body: JSON.stringify({ allowBlocking }),
  })

export const resetTraffic = () => request('/api/reset', { method: 'POST' })
