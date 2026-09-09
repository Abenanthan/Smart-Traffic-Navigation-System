import { useState } from 'react'
import { readTheme, saveTheme } from '../theme'

export default function ThemeToggle() {
  const [theme, setTheme] = useState(readTheme)
  const dark = theme === 'dark'

  function toggleTheme() {
    const next = dark ? 'light' : 'dark'
    saveTheme(next)
    setTheme(next)
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label="Dark theme"
      aria-pressed={dark}
      title={`Switch to ${dark ? 'light' : 'dark'} theme`}
      onClick={toggleTheme}
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none"
           stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
           strokeLinejoin="round" aria-hidden="true">
        {dark ? (
          <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
          </>
        ) : <path d="M20.5 14A8.5 8.5 0 0 1 10 3.5 8.5 8.5 0 1 0 20.5 14Z" />}
      </svg>
      {dark ? 'Light theme' : 'Dark theme'}
    </button>
  )
}
