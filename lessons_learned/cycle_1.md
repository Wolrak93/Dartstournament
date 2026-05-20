# Lessons Learned — Cycle 1: Foundation & Tournament Engine

## Context

Cycle 1 covered Tasks 1–9: project scaffolding, data models, Vorrunde logic,
KO bracket, Lightning Round, Match Flow Engine, Handicap Calculator,
Special Events Detection, and Bonus Points Aggregation.
All backend logic, no UI. 307 tests, all passing. Duration: 9 feature branches.

---

## Lessons

### 1. No GUI → Always provide manual test commands

When a development cycle produces no UI, the user has no way to interactively
test what a real user would do. Going forward: every feature branch that
produces testable logic should include a short "How to manually test this"
section in the implementation summary, for example:

```bash
# Run just the new tests
cd backend && .venv/Scripts/python.exe -m pytest tests/test_bonus.py -v

# Run a quick smoke check via Python REPL
cd backend && .venv/Scripts/python.exe -c "
from app.services.bonus import aggregate_bonus
from app.services.events import DetectedEvent, EventType
history = [(1, [DetectedEvent(EventType.GEWORFEN_180, 1, 1800)])]
print(aggregate_bonus(history))  # {1: 1800}
"
```

This applies to all future cycles without a deployed UI.

### 2. Duplicate EventType definition

`EventType` is defined in two places:
- `backend/app/models/special_event.py` (SQLAlchemy Enum for DB storage)
- `backend/app/services/events.py` (service-layer StrEnum)

Both exist for different reasons but have diverged in naming convention
(`score_26` vs `26_geworfen`). In Cycle 2, when API routes wire models to
services, this will cause confusion. Decision needed: either unify into one
canonical enum, or explicitly document which one to use where.

### 3. bonus_points not wired into record_match_result

`PlayerStanding.bonus_points` exists in `vorrunde.py` and `bonus.py`
provides `update_standing_bonus()`, but `record_match_result()` does not
call it automatically. The caller must invoke both functions manually.
This silent gap will likely cause a bug in Cycle 2 when the API layer
assembles the full match-result flow. Add a note in `record_match_result`
or extend its signature to accept bonus events before Cycle 2 API work.

### 4. All services are pure in-memory — DB integration is a Cycle 2 blank slate

Every service (vorrunde, ko, lightning, match, handicap, events, bonus)
takes plain Python objects and returns plain Python objects. No SQLAlchemy
session parameters anywhere. This was intentional for testability but means
the entire persistence layer still needs to be built in Cycle 2. Budget
significant effort for the "glue" work between services and DB.

### 5. process_visit always requires exactly 3 Dart objects

Even when a player finishes on the first dart, `process_visit` requires
exactly 3 `Dart` objects. The convention is: remaining darts after the
finishing dart are `Dart(score=0, band=DartBand.MISS, number=0)`.
This is correct game logic but unintuitive when writing tests — it tripped
up one test during Task 9. Document this in the `process_visit` docstring
and add a helper `_miss()` to the shared test utilities if a `conftest.py`
is introduced in Cycle 2.
