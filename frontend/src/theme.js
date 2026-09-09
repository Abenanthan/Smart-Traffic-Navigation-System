const STORAGE_KEY = 'smart-traffic-theme'

export function readTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

export function saveTheme(theme) {
  applyTheme(theme)
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Theme switching still works when browser storage is unavailable.
  }
}
