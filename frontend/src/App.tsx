import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { TournamentProvider } from './contexts/TournamentContext'
import BullThrowScreen from './screens/BullThrowScreen'
import ScoreEntryScreen from './screens/ScoreEntryScreen'
import HomeScreen from './screens/HomeScreen'
import SetupScreen from './screens/SetupScreen'
import StandingsScreen from './screens/StandingsScreen'
import BracketScreen from './screens/BracketScreen'
import LightningScreen from './screens/LightningScreen'
import NextMatchesScreen from './screens/NextMatchesScreen'

const router = createBrowserRouter([
  { path: '/', element: <HomeScreen /> },
  { path: '/setup', element: <SetupScreen /> },
  { path: '/bull-throw/:matchId', element: <BullThrowScreen /> },
  { path: '/score/:matchId', element: <ScoreEntryScreen /> },
  { path: '/walkon/:matchId', element: <div>Walk-on (Task 19)</div> },
  { path: '/standings', element: <StandingsScreen /> },
  { path: '/next-matches', element: <NextMatchesScreen /> },
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
