# Design Spec: Task 24 — Mobile Frontend Foundation

**Date:** 2026-06-07
**Branch:** `feature/mobile-frontend-foundation`
**Status:** Approved

---

## Goal

Lay the technical foundation for the mobile web interface:
auth utilities, authenticated API helpers, mobile TypeScript types,
layout and route guard components, routing, and 7 stub screens.

---

## 1. Auth Utilities

**File:** `frontend/src/mobile/mobileAuth.ts`

Token and player ID stored in `localStorage` under fixed keys:

- `mobile_token` — JWT string
- `mobile_player_id` — numeric player ID as string

### Functions

| Function | Behavior |
|---|---|
| `getToken()` | Returns `localStorage.getItem('mobile_token')` or `null` |
| `setToken(token, playerId?)` | Writes token; writes player ID if provided |
| `clearToken()` | Removes both keys |
| `isLoggedIn()` | `getToken() !== null` |
| `getStoredPlayerId()` | Returns `Number(item)` or `null` |

**Rationale for localStorage:** Token survives browser restarts — players log in once per tournament day.

---

## 2. Mobile TypeScript Types

**File:** `frontend/src/api/types.ts` (additions)

Mirrors `backend/app/schemas/mobile.py` exactly:

```typescript
// Auth
MobileLoginRequest  { player_id: number; pin: string }
MobileLoginResponse { token: string; player_id: number; name: string }

// Matches
MobileLiveMatch      { match_id, round_type, player1_id, player1_name, player2_id, player2_name }
MobileUpcomingMatch  { match_id, round_type, player1_name, player2_name }
MobileCompletedMatch { match_id, round_type, player1_name, player2_name, winner_name }
MobileMatchesResponse { tournament_id: number|null; live, upcoming, completed }

// Standings
MobileStandingEntry    { rank, player_id, name, wins, losses, avg_score, reg_points, bonus_points, ko_qualified }
MobileStandingsResponse { tournament_id: number|null; phase: string; entries }

// Bracket
MobileBracketMatch    { match_id: number|null; player1_name, player2_name, winner_name: string|null; is_completed }
MobileBracketRound    { label: string; matches }
MobileNebenrundeMatch { match_id, round_number, player1_name, player2_name, winner_name: string|null, is_completed }
MobileBracketResponse { tournament_id: number|null; ko_rounds, nebenrunde }

// Stats
MobilePlayerStats    { player_id, name, avg_score, wins, losses, bonus_points, event_counts: Record<string,number> }
MobileStatsResponse  { tournament_id: number|null; players, totals: Record<string,number> }

// Profile
MobileProfileResponse { player_id, name, photo_url: string|null, rank: number|null,
                        reg_points, bonus_points, wins, losses, avg_score }
```

---

## 3. API Client Additions

**File:** `frontend/src/api/client.ts`

### Private Authenticated Helpers

```typescript
async function apiGetAuth<T>(path: string): Promise<T>
async function apiPostAuth<T, B>(path: string, body?: B): Promise<T>
```

Both read `getToken()` from `mobileAuth` and set `Authorization: Bearer <token>`.
Error handling mirrors existing `apiGet`/`apiPost` pattern.

### Public Mobile API Functions

| Function | Method | Endpoint | Auth |
|---|---|---|---|
| `mobileLogin(playerId, pin)` | POST | `/mobile/auth/login` | No |
| `getMobileMatches()` | GET | `/mobile/matches` | Yes |
| `getMobileStandings()` | GET | `/mobile/standings` | Yes |
| `getMobileBracket()` | GET | `/mobile/bracket` | Yes |
| `getMobileStats()` | GET | `/mobile/stats` | Yes |
| `getMobileMe()` | GET | `/mobile/me` | Yes |

---

## 4. MobileLayout

**File:** `frontend/src/mobile/MobileLayout.tsx`

Minimal shell wrapping all mobile screens:

```tsx
<div className="mobile-layout">
  <header className="mobile-header">
    <h1>Backsberger Open</h1>
  </header>
  <main className="mobile-content">
    <Outlet />
  </main>
</div>
```

No logout button here — that belongs in the ProfilPage (Task 29).
No CSS file for now — styles added in later tasks.

---

## 5. MobileGuard

**File:** `frontend/src/mobile/MobileGuard.tsx`

```tsx
export default function MobileGuard() {
  if (!isLoggedIn()) {
    return <Navigate to="/mobile/login" replace />
  }
  return <Outlet />
}
```

`replace` prevents the login page from appearing in browser history after a successful login.

---

## 6. Route Tree

Added to `frontend/src/App.tsx` as a new top-level entry in the existing `createBrowserRouter` array:

```
/mobile                  → MobileLayout
  /mobile/login          → LoginScreen      (no guard — public)
  <MobileGuard>
    /mobile (index)      → HomeScreen
    /mobile/spiele       → SpielePage
    /mobile/vorrunde     → VorrundeSeite
    /mobile/bracket      → BracketPage
    /mobile/statistiken  → StatisticsPage
    /mobile/profil       → ProfilPage
  </MobileGuard>
```

`/mobile/login` is outside the guard to prevent redirect loops.
All 7 screens are stub components in `frontend/src/mobile/screens/`.

---

## 7. Stub Screens

**Directory:** `frontend/src/mobile/screens/`

7 files — each exports a single functional component returning a labeled `<div>`.
No CSS, no logic — purpose is TypeScript compilation and route binding only.

| File | Component | Route |
|---|---|---|
| `LoginScreen.tsx` | `LoginScreen` | `/mobile/login` |
| `HomeScreen.tsx` | `HomeScreen` | `/mobile` (index) |
| `SpielePage.tsx` | `SpielePage` | `/mobile/spiele` |
| `VorrundeSeite.tsx` | `VorrundeSeite` | `/mobile/vorrunde` |
| `BracketPage.tsx` | `BracketPage` | `/mobile/bracket` |
| `StatisticsPage.tsx` | `StatisticsPage` | `/mobile/statistiken` |
| `ProfilPage.tsx` | `ProfilPage` | `/mobile/profil` |

---

## 8. Tests

### `frontend/src/__tests__/mobileAuth.test.ts`

Uses jsdom's `localStorage` (provided by vitest's test environment):

- Token round-trip: `setToken('abc')` → `getToken() === 'abc'`
- `isLoggedIn()` false without token; true with token
- `setToken` with playerId → `getStoredPlayerId()` returns correct number
- `clearToken()` removes token and player ID; `isLoggedIn()` returns false

### `frontend/src/__tests__/MobileGuard.test.tsx`

- No token → component renders `<Navigate to="/mobile/login" />`
- Token present → renders children via `<Outlet>`
- `mobileAuth` module mocked via `vi.mock()` to control `isLoggedIn()` return value
- Uses `MemoryRouter` consistent with existing test patterns

---

## File Summary

```
frontend/src/
├── api/
│   ├── client.ts       — add apiGetAuth, apiPostAuth, 6 mobile functions
│   └── types.ts        — add 14 mobile TypeScript interfaces
├── mobile/
│   ├── mobileAuth.ts   — new: token storage utilities
│   ├── MobileLayout.tsx — new: header + Outlet wrapper
│   ├── MobileGuard.tsx  — new: auth redirect guard
│   └── screens/
│       ├── LoginScreen.tsx     — new stub
│       ├── HomeScreen.tsx      — new stub
│       ├── SpielePage.tsx      — new stub
│       ├── VorrundeSeite.tsx   — new stub
│       ├── BracketPage.tsx     — new stub
│       ├── StatisticsPage.tsx  — new stub
│       └── ProfilPage.tsx      — new stub
├── App.tsx             — add /mobile/* route tree
└── __tests__/
    ├── mobileAuth.test.ts    — new
    └── MobileGuard.test.tsx  — new
```
