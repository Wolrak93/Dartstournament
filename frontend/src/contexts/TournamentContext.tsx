import { createContext, useContext, useState, type ReactNode } from 'react'

interface TournamentContextType {
  tournamentId: number | null
  currentMatchId: number | null
  setTournamentId: (id: number | null) => void
  setCurrentMatchId: (id: number | null) => void
}

const TournamentContext = createContext<TournamentContextType | null>(null)

export function TournamentProvider({ children }: { children: ReactNode }) {
  const [tournamentId, setTournamentId] = useState<number | null>(null)
  const [currentMatchId, setCurrentMatchId] = useState<number | null>(null)

  return (
    <TournamentContext.Provider
      value={{ tournamentId, currentMatchId, setTournamentId, setCurrentMatchId }}
    >
      {children}
    </TournamentContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTournament(): TournamentContextType {
  const ctx = useContext(TournamentContext)
  if (!ctx) throw new Error('useTournament must be used within TournamentProvider')
  return ctx
}
