# Task 24 — Mobile Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auth utilities, authenticated API helpers, mobile TypeScript types, MobileLayout, MobileGuard, 7 stub screens, and a `/mobile/*` route tree to the existing React frontend.

**Architecture:** A `frontend/src/mobile/` directory holds all mobile-specific infrastructure. Token management lives in `mobileAuth.ts` (localStorage). `MobileGuard` uses `isLoggedIn()` from `mobileAuth` to redirect unauthenticated users. The `/mobile/*` route tree nests under `MobileLayout` in the existing `createBrowserRouter`.

**Tech Stack:** React 19, React Router v6 (`createBrowserRouter`, `Outlet`, `Navigate`), TypeScript, Vitest + @testing-library/react, localStorage for token persistence.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/api/types.ts` | Add 14 mobile TypeScript interfaces |
| Create | `frontend/src/mobile/mobileAuth.ts` | Token storage utilities (get/set/clear/isLoggedIn/getStoredPlayerId) |
| Modify | `frontend/src/api/client.ts` | Add `apiGetAuth`, `apiPostAuth` and 6 mobile API functions |
| Create | `frontend/src/mobile/MobileLayout.tsx` | Minimal header + Outlet wrapper |
| Create | `frontend/src/mobile/MobileGuard.tsx` | Auth redirect guard (`isLoggedIn` → Outlet or Navigate) |
| Create | `frontend/src/mobile/screens/LoginScreen.tsx` | Stub |
| Create | `frontend/src/mobile/screens/HomeScreen.tsx` | Stub |
| Create | `frontend/src/mobile/screens/SpielePage.tsx` | Stub |
| Create | `frontend/src/mobile/screens/VorrundeSeite.tsx` | Stub |
| Create | `frontend/src/mobile/screens/BracketPage.tsx` | Stub |
| Create | `frontend/src/mobile/screens/StatisticsPage.tsx` | Stub |
| Create | `frontend/src/mobile/screens/ProfilPage.tsx` | Stub |
| Modify | `frontend/src/App.tsx` | Add `/mobile/*` route tree |
| Create | `frontend/src/__tests__/mobileAuth.test.ts` | Tests for mobileAuth utilities |
| Create | `frontend/src/__tests__/MobileGuard.test.tsx` | Tests for MobileGuard redirect behavior |

---

## Task 1: Mobile TypeScript Types

**Files:**
- Modify: `frontend/src/api/types.ts` (append after line 205)

- [ ] **Step 1: Append mobile interfaces to `types.ts`**

Add the following block at the very end of `frontend/src/api/types.ts`:

```typescript
// ---------------------------------------------------------------------------
// Mobile interfaces
// ---------------------------------------------------------------------------

export interface MobileLoginRequest {
  player_id: number
  pin: string
}

export interface MobileLoginResponse {
  token: string
  player_id: number
  name: string
}

export interface MobileLiveMatch {
  match_id: number
  round_type: string
  player1_id: number
  player1_name: string
  player2_id: number
  player2_name: string
}

export interface MobileUpcomingMatch {
  match_id: number
  round_type: string
  player1_name: string
  player2_name: string
}

export interface MobileCompletedMatch {
  match_id: number
  round_type: string
  player1_name: string
  player2_name: string
  winner_name: string
}

export interface MobileMatchesResponse {
  tournament_id: number | null
  live: MobileLiveMatch[]
  upcoming: MobileUpcomingMatch[]
  completed: MobileCompletedMatch[]
}

export interface MobileStandingEntry {
  rank: number
  player_id: number
  name: string
  wins: number
  losses: number
  avg_score: number
  reg_points: number
  bonus_points: number
  ko_qualified: boolean
}

export interface MobileStandingsResponse {
  tournament_id: number | null
  phase: string
  entries: MobileStandingEntry[]
}

export interface MobileBracketMatch {
  match_id: number | null
  player1_name: string | null
  player2_name: string | null
  winner_name: string | null
  is_completed: boolean
}

export interface MobileBracketRound {
  label: string
  matches: MobileBracketMatch[]
}

export interface MobileNebenrundeMatch {
  match_id: number
  round_number: number
  player1_name: string
  player2_name: string
  winner_name: string | null
  is_completed: boolean
}

export interface MobileBracketResponse {
  tournament_id: number | null
  ko_rounds: MobileBracketRound[]
  nebenrunde: MobileNebenrundeMatch[]
}

export interface MobilePlayerStats {
  player_id: number
  name: string
  avg_score: number
  wins: number
  losses: number
  bonus_points: number
  event_counts: Record<string, number>
}

export interface MobileStatsResponse {
  tournament_id: number | null
  players: MobilePlayerStats[]
  totals: Record<string, number>
}

export interface MobileProfileResponse {
  player_id: number
  name: string
  photo_url: string | null
  rank: number | null
  reg_points: number
  bonus_points: number
  wins: number
  losses: number
  avg_score: number
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "feat: add mobile TypeScript interfaces to types.ts"
```

---

## Task 2: Auth Utilities (TDD)

**Files:**
- Create: `frontend/src/__tests__/mobileAuth.test.ts`
- Create: `frontend/src/mobile/mobileAuth.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/mobileAuth.test.ts`:

```typescript
import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearToken,
  getStoredPlayerId,
  getToken,
  isLoggedIn,
  setToken,
} from '../mobile/mobileAuth'

describe('mobileAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('getToken returns null when no token is set', () => {
    expect(getToken()).toBeNull()
  })

  it('setToken stores the token and getToken retrieves it', () => {
    setToken('abc123')
    expect(getToken()).toBe('abc123')
  })

  it('isLoggedIn returns false without a token', () => {
    expect(isLoggedIn()).toBe(false)
  })

  it('isLoggedIn returns true after setToken', () => {
    setToken('tok')
    expect(isLoggedIn()).toBe(true)
  })

  it('setToken with playerId stores the player id', () => {
    setToken('tok', 42)
    expect(getStoredPlayerId()).toBe(42)
  })

  it('getStoredPlayerId returns null when not set', () => {
    expect(getStoredPlayerId()).toBeNull()
  })

  it('clearToken removes token and player id', () => {
    setToken('tok', 5)
    clearToken()
    expect(getToken()).toBeNull()
    expect(getStoredPlayerId()).toBeNull()
    expect(isLoggedIn()).toBe(false)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `frontend/`:
```bash
npm run test:run -- src/__tests__/mobileAuth.test.ts
```
Expected: FAIL — `Cannot find module '../mobile/mobileAuth'`

- [ ] **Step 3: Implement `mobileAuth.ts`**

Create `frontend/src/mobile/mobileAuth.ts`:

```typescript
const TOKEN_KEY = 'mobile_token'
const PLAYER_ID_KEY = 'mobile_player_id'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string, playerId?: number): void {
  localStorage.setItem(TOKEN_KEY, token)
  if (playerId !== undefined) {
    localStorage.setItem(PLAYER_ID_KEY, String(playerId))
  }
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(PLAYER_ID_KEY)
}

export function isLoggedIn(): boolean {
  return getToken() !== null
}

export function getStoredPlayerId(): number | null {
  const val = localStorage.getItem(PLAYER_ID_KEY)
  return val !== null ? Number(val) : null
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `frontend/`:
```bash
npm run test:run -- src/__tests__/mobileAuth.test.ts
```
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/__tests__/mobileAuth.test.ts frontend/src/mobile/mobileAuth.ts
git commit -m "feat: add mobile auth utilities with localStorage token storage"
```

---

## Task 3: Authenticated API Helpers & Mobile API Functions

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add import and authenticated helpers**

At the top of `frontend/src/api/client.ts`, add the import after the existing type imports:

```typescript
import { getToken } from '../mobile/mobileAuth'
```

Then add two new private helpers directly after the existing `apiPost` function (before the `// Player endpoints` comment):

```typescript
async function apiGetAuth<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${getToken() ?? ''}` },
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

async function apiPostAuth<T, B = unknown>(path: string, body?: B): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken() ?? ''}`,
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}
```

- [ ] **Step 2: Add mobile type imports to client.ts**

Replace the existing `import type { ... } from './types'` block at the top of `client.ts` with this expanded version:

```typescript
import type {
  Player,
  Tournament,
  TournamentDetail,
  TournamentCreateRequest,
  StandingEntry,
  MatchRead,
  BullThrowRequest,
  BullThrowResponse,
  KOBracketResponse,
  LightningResponse,
  VisitRequest,
  VisitResponse,
  VisitHistoryItem,
  MatchStateResponse,
  MobileLoginRequest,
  MobileLoginResponse,
  MobileMatchesResponse,
  MobileStandingsResponse,
  MobileBracketResponse,
  MobileStatsResponse,
  MobileProfileResponse,
} from './types'
```

- [ ] **Step 3: Add mobile API functions**

Append these at the end of `frontend/src/api/client.ts`:

```typescript
// ---------------------------------------------------------------------------
// Mobile endpoints
// ---------------------------------------------------------------------------

export const mobileLogin = (
  playerId: number,
  pin: string,
): Promise<MobileLoginResponse> =>
  apiPost<MobileLoginResponse, MobileLoginRequest>('/mobile/auth/login', {
    player_id: playerId,
    pin,
  })

export const getMobileMatches = (): Promise<MobileMatchesResponse> =>
  apiGetAuth<MobileMatchesResponse>('/mobile/matches')

export const getMobileStandings = (): Promise<MobileStandingsResponse> =>
  apiGetAuth<MobileStandingsResponse>('/mobile/standings')

export const getMobileBracket = (): Promise<MobileBracketResponse> =>
  apiGetAuth<MobileBracketResponse>('/mobile/bracket')

export const getMobileStats = (): Promise<MobileStatsResponse> =>
  apiGetAuth<MobileStatsResponse>('/mobile/stats')

export const getMobileMe = (): Promise<MobileProfileResponse> =>
  apiGetAuth<MobileProfileResponse>('/mobile/me')
```

- [ ] **Step 4: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add authenticated API helpers and mobile API functions"
```

---

## Task 4: MobileLayout

**Files:**
- Create: `frontend/src/mobile/MobileLayout.tsx`

- [ ] **Step 1: Create `MobileLayout.tsx`**

Create `frontend/src/mobile/MobileLayout.tsx`:

```tsx
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
```

- [ ] **Step 2: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/mobile/MobileLayout.tsx
git commit -m "feat: add MobileLayout with header and Outlet"
```

---

## Task 5: Stub Screens

**Files:**
- Create: `frontend/src/mobile/screens/LoginScreen.tsx`
- Create: `frontend/src/mobile/screens/HomeScreen.tsx`
- Create: `frontend/src/mobile/screens/SpielePage.tsx`
- Create: `frontend/src/mobile/screens/VorrundeSeite.tsx`
- Create: `frontend/src/mobile/screens/BracketPage.tsx`
- Create: `frontend/src/mobile/screens/StatisticsPage.tsx`
- Create: `frontend/src/mobile/screens/ProfilPage.tsx`

- [ ] **Step 1: Create all 7 stub screen files**

Create `frontend/src/mobile/screens/LoginScreen.tsx`:
```tsx
export default function LoginScreen() {
  return <div>LoginScreen</div>
}
```

Create `frontend/src/mobile/screens/HomeScreen.tsx`:
```tsx
export default function HomeScreen() {
  return <div>HomeScreen</div>
}
```

Create `frontend/src/mobile/screens/SpielePage.tsx`:
```tsx
export default function SpielePage() {
  return <div>SpielePage</div>
}
```

Create `frontend/src/mobile/screens/VorrundeSeite.tsx`:
```tsx
export default function VorrundeSeite() {
  return <div>VorrundeSeite</div>
}
```

Create `frontend/src/mobile/screens/BracketPage.tsx`:
```tsx
export default function BracketPage() {
  return <div>BracketPage</div>
}
```

Create `frontend/src/mobile/screens/StatisticsPage.tsx`:
```tsx
export default function StatisticsPage() {
  return <div>StatisticsPage</div>
}
```

Create `frontend/src/mobile/screens/ProfilPage.tsx`:
```tsx
export default function ProfilPage() {
  return <div>ProfilPage</div>
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/mobile/screens/
git commit -m "feat: add 7 mobile stub screens"
```

---

## Task 6: MobileGuard (TDD)

**Files:**
- Create: `frontend/src/__tests__/MobileGuard.test.tsx`
- Create: `frontend/src/mobile/MobileGuard.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/__tests__/MobileGuard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../mobile/mobileAuth', () => ({
  isLoggedIn: vi.fn(),
}))

import { isLoggedIn } from '../mobile/mobileAuth'
import MobileGuard from '../mobile/MobileGuard'

describe('MobileGuard', () => {
  it('redirects to /mobile/login when not logged in', () => {
    vi.mocked(isLoggedIn).mockReturnValue(false)

    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route element={<MobileGuard />}>
            <Route path="/mobile" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders child route when logged in', () => {
    vi.mocked(isLoggedIn).mockReturnValue(true)

    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route element={<MobileGuard />}>
            <Route path="/mobile" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `frontend/`:
```bash
npm run test:run -- src/__tests__/MobileGuard.test.tsx
```
Expected: FAIL — `Cannot find module '../mobile/MobileGuard'`

- [ ] **Step 3: Implement `MobileGuard.tsx`**

Create `frontend/src/mobile/MobileGuard.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { isLoggedIn } from './mobileAuth'

export default function MobileGuard() {
  if (!isLoggedIn()) {
    return <Navigate to="/mobile/login" replace />
  }
  return <Outlet />
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `frontend/`:
```bash
npm run test:run -- src/__tests__/MobileGuard.test.tsx
```
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/__tests__/MobileGuard.test.tsx frontend/src/mobile/MobileGuard.tsx
git commit -m "feat: add MobileGuard with auth redirect and tests"
```

---

## Task 7: Route Tree in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add mobile imports to `App.tsx`**

Add these imports after the existing screen imports (after `WalkOnScreen`):

```typescript
import MobileLayout from './mobile/MobileLayout'
import MobileGuard from './mobile/MobileGuard'
import LoginScreen from './mobile/screens/LoginScreen'
import MobileHome from './mobile/screens/HomeScreen'
import SpielePage from './mobile/screens/SpielePage'
import VorrundeSeite from './mobile/screens/VorrundeSeite'
import BracketPage from './mobile/screens/BracketPage'
import StatisticsPage from './mobile/screens/StatisticsPage'
import ProfilPage from './mobile/screens/ProfilPage'
```

Note: `HomeScreen` is aliased as `MobileHome` to avoid collision with the existing `HomeScreen` import from `./screens/HomeScreen`.

- [ ] **Step 2: Add the `/mobile` route tree**

In the `createBrowserRouter` array in `App.tsx`, append the `/mobile` entry after the existing `/lightning` route:

```typescript
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
```

- [ ] **Step 3: Verify TypeScript compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: add /mobile/* route tree with MobileLayout and MobileGuard"
```

---

## Task 8: Final Verification

- [ ] **Step 1: Run the full test suite**

Run from `frontend/`:
```bash
npm run test:run
```
Expected: all existing tests + 9 new mobile tests PASS, 0 failures.

- [ ] **Step 2: Run the linter**

Run from `frontend/`:
```bash
npm run lint
```
Expected: no errors.

- [ ] **Step 3: Run TypeScript type check**

Run from `frontend/`:
```bash
npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit verification result**

No new files to commit — this is a verification step only.

---

## Summary

After all tasks complete, the following is in place:

- `mobile/mobileAuth.ts` — 5 token functions, 7 tests passing
- `api/types.ts` — 14 mobile interfaces added
- `api/client.ts` — `apiGetAuth`, `apiPostAuth`, 6 mobile API functions
- `mobile/MobileLayout.tsx` — header + Outlet
- `mobile/MobileGuard.tsx` — auth redirect, 2 tests passing
- `mobile/screens/` — 7 stub components
- `App.tsx` — `/mobile/*` route tree with 7 routes
