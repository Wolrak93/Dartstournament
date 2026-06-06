# Design Spec — Cycle 3: Mobile Web Interface

Date: 2026-06-07

## Goal

Build a mobile-first web interface for players and spectators (including remote viewers via Cloudflare Tunnel) to follow the Backsberger Open tournament live. All content is behind login. Real-time updates via WebSocket.

---

## Deployment

**Cloudflare Tunnel** — backend runs on the Windows referee PC. Before the tournament, a Cloudflare Tunnel is started (single CLI command), giving remote spectators a public URL. After the tournament it is stopped. Local devices on the same network access the PC's LAN IP directly.

- No cloud infrastructure, no permanent hosting cost.
- If the home internet drops, remote access is interrupted but the local tournament continues unaffected.
- The tunnel wraps the existing FastAPI server (port unchanged).

---

## Architecture

The mobile interface is built inside the **existing React/Vite frontend** as a `/mobile/*` route tree. No separate app, no separate build.

```
/                    Existing referee screens (unchanged)
/mobile/login        Login screen
/mobile              Home — 6 tiles
/mobile/spiele       Spiele screen
/mobile/vorrunde     Vorrunde table
/mobile/bracket      KO-Bracket (2 tabs: KO + Nebenrunde)
/mobile/statistiken  Statistics
/mobile/profil       Own player profile
```

**Shared between referee and mobile:**
- `useWebSocket` hook
- API utility functions
- TypeScript model types

**New in Cycle 3:**
- `MobileLayout` wrapper component (header, back-to-home navigation)
- One page component per route above
- New REST endpoints under `/mobile/*` in FastAPI
- Auth: `POST /mobile/auth/login` → JWT stored in `localStorage`

---

## Authentication

- All `/mobile/*` routes (except `/mobile/login`) are protected by a `MobileGuard` component. Unauthenticated requests redirect to `/mobile/login`.
- Login: user selects their name from a dropdown, enters a 4-digit PIN.
- Token stored in `localStorage`. No session expiry during the tournament.
- No sensitive data — PIN is purely a lightweight access control.
- PINs are set once per player/spectator in the backend (e.g. via a seed script or admin endpoint) before the tournament starts. No self-registration flow needed.

---

## Real-time Strategy

- The `Spiele` screen connects to the existing WebSocket and receives live score updates in real-time.
- All other screens (`Vorrunde`, `Bracket`, `Statistiken`, `Profil`) load via REST on mount, then refresh whenever a relevant WebSocket event is received (e.g. `match_score_updated`, `match_completed`).
- Mobile clients are **read-only** — they never send data via WebSocket.

---

## Navigation — Home Screen

6 tiles in a 2×3 grid. Tiles 1–5 are active in Cycle 3. Tile 6 is disabled (Cycle 4).

| # | Tile | Subtext | Status |
|---|------|---------|--------|
| 1 | ⚡ Spiele | 1 Match aktiv | Active |
| 2 | 📊 Vorrunde | Tabelle | Active |
| 3 | 🏆 KO-Bracket | Viertelfinale | Active |
| 4 | 📈 Statistiken | Gesamt + Spieler | Active |
| 5 | 👤 Profil | Foto + Stats | Active |
| 6 | ¥$ Wetten | Coming soon | Disabled (Cycle 4) |

The subtext of active tiles is dynamic (e.g. current round, current phase).

---

## Screen Designs

### Login (`/mobile/login`)

- Tournament logo + title centered.
- Name dropdown (all registered players + spectators).
- 4-digit PIN entry (4 boxes, filled as user types).
- "Anmelden" button → POST `/mobile/auth/login` → redirect to `/mobile`.

---

### Spiele (`/mobile/spiele`)

Three sections, top to bottom:

1. **LIVE** — currently active match with real-time WebSocket updates:
   - Player names, remaining score for each (large), current visit number, who is at the oche.
2. **NÄCHSTE MATCHES** — upcoming match queue (round label + player names).
3. **ABGESCHLOSSEN** — completed matches with final result (winner + scoreline).

---

### Vorrunde (`/mobile/vorrunde`)

Standings table. Columns: Rank, Name, W/L, Average, Regular Points, Bonus Points.

- Rows for KO-qualified players (top 6 by regular points) highlighted in green.
- Loaded via REST, refreshed on `match_completed` WebSocket event.

---

### KO-Bracket (`/mobile/bracket`)

Two tabs within the same screen:

**Tab 1 — KO:**
- Bracket sections: Viertelfinale → Halbfinale → Finale.
- Completed matches shown in green with result; pending matches shown in gray with "vs".

**Tab 2 — Nebenrunde:**
- Results list of Lightning Round matches, grouped by round.

Both tabs refresh on `match_completed` WebSocket event.

---

### Statistiken (`/mobile/statistiken`)

- **Spieler-Dropdown** at the top: defaults to "Alle Spieler", can be narrowed to one player.
- **Top Averages** — horizontal bar chart, all players ranked.
- **Besondere Ereignisse** — highlight tiles: 180er count, total Bonus Points, Bulls Eyes, Tripel 20 (totals across all players, or per-player when filtered).
- Loaded via REST, refreshed on `match_completed` WebSocket event.

---

### Profil (`/mobile/profil`)

Shows the logged-in player's own profile. Sections top to bottom:

1. **Photo** (player image from `user_input/pics/`), nickname, fun fact.
2. **Aktueller Stand** — current rank + points (highlighted card).
3. **Spielstärke-Profil** — σ normal, σ stark, starke Felder. Shown as disabled/grayed out with "Coming soon (Cycle 6)". Structure is in place for Cycle 6 activation.
4. **Meine Stats** — W/L, Average, 180er count, Bonus Points.

---

## New Backend Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/mobile/auth/login` | Name + PIN → JWT |
| GET | `/mobile/matches` | All matches: live, upcoming, completed |
| GET | `/mobile/standings` | Vorrunde table |
| GET | `/mobile/bracket` | KO + Nebenrunde bracket data |
| GET | `/mobile/stats` | Aggregated + per-player statistics |
| GET | `/mobile/me` | Logged-in player profile data |

All GET endpoints require a valid JWT in the `Authorization` header.

---

## "Coming Soon" Placeholders

Consistent pattern across cycles — disabled sections are visually present but grayed out with dashed border and "Coming soon (Cycle X)" label.

| Section | Cycle |
|---------|-------|
| ¥$ Wetten tile (Home) | Cycle 4 |
| Spielstärke-Profil (Profil screen) | Cycle 6 |

---

## Out of Scope (Cycle 3)

- Betting functionality (Cycle 4)
- Spielstärke-Profil editing and Monte Carlo checkout generation (Cycle 6)
- Push notifications
- Offline/PWA support
