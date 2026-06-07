# Deployment Guide — Backsberger Open

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/) installed
- Node.js 20+ with npm

## Backend Setup

```bash
cd backend
uv sync
```

## Frontend Setup

```bash
cd frontend
npm install
```

## Setting Player PINs

Before the tournament starts, assign a 4-digit PIN to each player so they can log in on the mobile interface.

1. Open `backend/scripts/set_pins.py` and edit the `PINS` dictionary:

   ```python
   PINS: dict[str, str] = {
       "Lars":    "1234",
       "Mike":    "5678",
       "Philipp": "9012",
       # ...
   }
   ```

   Each key must match the player's exact name as stored in the database.

2. Run the script from the `backend/` directory:

   ```bash
   cd backend
   uv run python scripts/set_pins.py
   ```

3. The script prints which players were updated and warns about any names not found in the database.

## Running the App

**Backend:**

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm run dev
```

## Remote Access (Cloudflare Tunnel)

To make the mobile interface reachable on players' phones:

```bash
cloudflared tunnel --url http://localhost:5173
```

The CORS policy is already set to `["*"]` to allow cross-origin requests from the tunnel URL.
