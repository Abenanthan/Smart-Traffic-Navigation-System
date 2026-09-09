import React from 'react'
import ReactDOM from 'react-dom/client'
import ExperienceRouter from './ExperienceRouter.jsx'
import './styles.css'
import { applyTheme, readTheme } from './theme'

// Restore the saved palette before mounting the interface.
applyTheme(readTheme())

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ExperienceRouter />
  </React.StrictMode>,
)
