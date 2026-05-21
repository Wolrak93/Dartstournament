import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { TournamentProvider } from './contexts/TournamentContext'
import BullThrowScreen from './screens/BullThrowScreen'
import SetupScreen from './screens/SetupScreen'
import StandingsScreen from './screens/StandingsScreen'
import BracketScreen from './screens/BracketScreen'
import LightningScreen from './screens/LightningScreen'

const router = createBrowserRouter([
  { path: '/', element: <SetupScreen /> },
  { path: '/setup', element: <SetupScreen /> },
  { path: '/bull-throw/:matchId', element: <BullThrowScreen /> },
  { path: '/score/:matchId', element: <div>Score Entry (Task 16)</div> },
  { path: '/walkon/:matchId', element: <div>Walk-on (Task 19)</div> },
  { path: '/standings', element: <StandingsScreen /> },
  { path: '/bracket', element: <BracketScreen /> },
  { path: '/lightning', element: <LightningScreen /> },
])

export default function App() {
  return (
    <TournamentProvider>
      <RouterProvider router={router} />
    </TournamentProvider>
  )
}
