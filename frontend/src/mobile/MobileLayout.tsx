import { Outlet } from 'react-router-dom'

export default function MobileLayout() {
  return (
    <div className="mobile-layout">
      <header className="mobile-header">
        <h1>Backsberger Open</h1>
      </header>
      <main className="mobile-content">
        <Outlet />
      </main>
    </div>
  )
}
