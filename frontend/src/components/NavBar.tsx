import { NavLink } from 'react-router-dom'
import './NavBar.css'

export default function NavBar() {
  return (
    <nav className="nav-bar">
      <NavLink
        to="/standings"
        className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
      >
        Standings
      </NavLink>
      <NavLink
        to="/bracket"
        className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
      >
        KO Bracket
      </NavLink>
      <NavLink
        to="/lightning"
        className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
      >
        Lightning
      </NavLink>
    </nav>
  )
}
