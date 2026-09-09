import { lazy, Suspense } from 'react'
import App from './App'
import './experience-navigation.css'

const RealMapNavigationPage = lazy(() => import('./pages/RealMapNavigationPage'))

export default function ExperienceRouter() {
  const realMap = window.location.pathname.replace(/\/$/, '') === '/real-map'
  return (
    <>
      <nav className="experience-nav" aria-label="Navigation experiences">
        <a href="/" aria-current={!realMap ? 'page' : undefined}>AI Simulation</a>
        <a href="/real-map" aria-current={realMap ? 'page' : undefined}>Real Map Navigation</a>
        <span>Smart Traffic Navigation · UCS</span>
      </nav>
      {realMap ? (
        <Suspense fallback={<div className="empty-state" role="status">Loading Real Map Navigation…</div>}>
          <RealMapNavigationPage />
        </Suspense>
      ) : <App />}
    </>
  )
}
