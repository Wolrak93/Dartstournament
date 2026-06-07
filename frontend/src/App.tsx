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
import WalkOnScreen from './screens/WalkOnScreen'
import MobileLayout from './mobile/MobileLayout'
import MobileGuard from './mobile/MobileGuard'
import LoginScreen from './mobile/screens/LoginScreen'
import MobileHome from './mobile/screens/HomeScreen'
import SpielePage from './mobile/screens/SpielePage'
import VorrundeSeite from './mobile/screens/VorrundeSeite'
import BracketPage from './mobile/screens/BracketPage'
import StatisticsPage from './mobile/screens/StatisticsPage'
import ProfilPage from './mobile/screens/ProfilPage'

const router = createBrowserRouter([
  { path: '/', element: <HomeScreen /> },
  { path: '/setup', element: <SetupScreen /> },
  { path: '/bull-throw/:matchId', element: <BullThrowScreen /> },
  { path: '/score/:matchId', element: <ScoreEntryScreen /> },
  { path: '/walkon/:matchId', element: <WalkOnScreen /> },
  { path: '/standings', element: <StandingsScreen /> },
  { path: '/next-matches', element: <NextMatchesScreen /> },
  { path: '/bracket', element: <BracketScreen /> },
  { path: '/lightning', element: <LightningScreen /> },
  {
    path: '/mobile',
    element: <MobileLayout />,
    children: [
      { path: 'login', element: <LoginScreen /> },
      {
        element: <MobileGuard />,
        children: [
          { index: true, element: <MobileHome /> },
          { path: 'spiele', element: <SpielePage /> },
          { path: 'vorrunde', element: <VorrundeSeite /> },
          { path: 'bracket', element: <BracketPage /> },
          { path: 'statistiken', element: <StatisticsPage /> },
          { path: 'profil', element: <ProfilPage /> },
        ],
      },
    ],
  },
])

export default function App() {
  return (
    <TournamentProvider>
      <RouterProvider router={router} />
    </TournamentProvider>
  )
}
