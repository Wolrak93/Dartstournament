import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { TournamentProvider } from './contexts/TournamentContext'
import SetupScreen from './screens/SetupScreen'

const router = createBrowserRouter([
  { path: '/', element: <SetupScreen /> },
  { path: '/setup', element: <SetupScreen /> },
  { path: '/bull-throw/:matchId', element: <div>Bull Throw (Task 15)</div> },
  { path: '/score/:matchId', element: <div>Score Entry (Task 16)</div> },
  { path: '/walkon/:matchId', element: <div>Walk-on (Task 19)</div> },
  { path: '/standings', element: <div>Standings (Task 20)</div> },
  { path: '/bracket', element: <div>KO Bracket (Task 20)</div> },
  { path: '/lightning', element: <div>Lightning Round (Task 20)</div> },
])

export default function App() {
  return (
    <TournamentProvider>
      <RouterProvider router={router} />
    </TournamentProvider>
  )
}
