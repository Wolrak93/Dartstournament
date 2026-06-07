import { Navigate, Outlet } from 'react-router-dom'
import { isLoggedIn } from './mobileAuth'

export default function MobileGuard() {
  if (!isLoggedIn()) {
    return <Navigate to="/mobile/login" replace />
  }
  return <Outlet />
}
