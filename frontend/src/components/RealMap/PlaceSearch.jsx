import { useEffect, useRef, useState } from 'react'
import { searchPlaces } from '../../realMapApi'

export default function PlaceSearch({ id, selected, disabled, bias, onSelect, onClear }) {
  const [query, setQuery] = useState(selected?.name || '')
  const [results, setResults] = useState([])
  const [status, setStatus] = useState('')
  const [searching, setSearching] = useState(false)
  const pending = useRef(null)
  const editing = useRef(false)
  useEffect(() => {
    pending.current?.abort()
    if (!editing.current) setQuery(selected?.name || '')
    editing.current = false
    setResults([])
    setStatus('')
    setSearching(false)
  }, [selected])
  useEffect(() => () => pending.current?.abort(), [])

  async function search() {
    if (query.trim().length < 2 || disabled) return
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    setSearching(true)
    setStatus('Searching places…')
    setResults([])
    try {
      const data = await searchPlaces(query.trim(), bias, controller.signal)
      if (controller.signal.aborted) return
      setResults(data.places)
      setStatus(data.places.length ? `${data.places.length} results. Select a place below.` : 'No places found. Include a city or try a different spelling.')
    } catch (error) {
      if (!controller.signal.aborted) setStatus(error.message)
    } finally {
      if (!controller.signal.aborted) setSearching(false)
    }
  }

  return <div className="rm-place-search">
    <div className="rm-search-row">
      <input id={id} value={query} title={selected?.name || undefined} disabled={disabled} placeholder="Search a place, address or city" autoComplete="off"
        onChange={event => { pending.current?.abort(); setSearching(false); setResults([]); setStatus(''); setQuery(event.target.value); if (selected) { editing.current = true; onClear() } }}
        onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); search() } }} />
      <button type="button" className="ghost small" disabled={disabled || searching || query.trim().length < 2} onClick={search}>Search</button>
    </div>
    {status && <p className="rm-inline-note" role="status">{status}</p>}
    {!!results.length && <ul className="rm-search-results" aria-label="Place search results">{results.map((place, index) =>
      <li key={`${place.latitude}-${place.longitude}-${index}`}><button type="button" disabled={disabled} onClick={() => onSelect(place)}>{place.name}<small>{place.latitude.toFixed(5)}, {place.longitude.toFixed(5)}</small></button></li>
    )}</ul>}
  </div>
}
