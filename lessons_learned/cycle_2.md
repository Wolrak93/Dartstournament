# Lessons Learned — Cycle 2: Main Screen UI & API Layer

## What Went Well

- Branch structure (feature → development) was used consistently throughout the cycle
- Strong test coverage gave real safety: 401 backend + 110 frontend tests all green at cycle end
- WebSocket + REST API separation was clean; the `useWebSocket` hook kept frontend code readable
- Walk-on screen with music worked out well

## What Was Difficult / Areas for Improvement

### Use the Superpowers plugin from day one — especially for UI design

The Superpowers plugin (particularly the brainstorming skill with visual companion) was not yet available at the start of Cycle 2. For UI design tasks, this meant more back-and-forth iterations to converge on the right layout and behavior. Time was wasted optimizing designs that could have been settled faster with upfront visual mockups.

**For Cycle 3 and beyond:** Invoke the brainstorming skill with the visual companion before starting any screen design. Present mockup options early and get approval before writing a single line of component code.

### ScoreEntryScreen grew too large

The score entry screen accumulated a lot of logic and became a large, hard-to-navigate file. In Cycle 3, consider splitting it into smaller focused components (scoreboard, numpad, checkout panel, overlays).

### Backend tests must be run from the `backend/` subdirectory

Running `uv run python -m pytest` from the repo root does not work — tests must be started from `backend/`. This trips up the workflow. Consider adding a root-level convenience script or Makefile entry in Cycle 3.

### Mixed line endings (CRLF warnings) on Windows

Some files produce CRLF warnings from Git. Not blocking, but worth enforcing a consistent `.gitattributes` setting early in Cycle 3.
