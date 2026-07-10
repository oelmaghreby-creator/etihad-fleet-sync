# Etihad Fleet Sync (free, automatic)

Pulls Etihad Airways' **current** fleet from live ADS-B (`airplanes.live`, no key, no quota),
identifies Etihad by callsign `ETD*` + UAE registration `A6-*`, and **accumulates** tails into
`etihad_fleet.json`. Runs unattended in **GitHub Actions** (free). Power Automate reads the JSON
and upserts your SharePoint list.

## Why this design
- **Free & no quota** — airplanes.live is open; GitHub Actions minutes are free (public repo).
- **Current** — live ADS-B has today's jets (A350-1000 `A6-XW*`, 787-10, A321neo) that the free
  static databases (OpenSky) are missing.
- **Complete over time** — one sweep sees only airborne jets (~60–70). Every 3h it accumulates;
  within ~2 days you reach the full ~120+ fleet. Not-seen-in-30-days → `Active=false` (soft-retire).

## Setup (one time, ~5 min)
1. Create a **new GitHub repo** (public = unlimited free Actions), e.g. `etihad-fleet-sync`.
2. Add these files to it (`sync.py`, `.github/workflows/etihad-fleet.yml`), commit & push.
3. Repo → **Actions** tab → enable workflows. Click **Etihad Fleet Sync → Run workflow** once to seed.
4. Your data is now at the **raw URL**:
   `https://raw.githubusercontent.com/<you>/etihad-fleet-sync/main/etihad_fleet.json`

The workflow re-runs every 3 hours and commits the updated JSON automatically.

## Power Automate consumption flow (simple — no premium API quota)
Trigger: **Recurrence** (weekly, or daily).
1. **HTTP** GET the raw URL above. *(This is the only premium connector call; it never hits an API quota.)*
2. **Parse JSON** — content `@body('HTTP')`. Schema: array of objects with
   `Title, Typecode, ICAO24, Model, Operator, Active, FirstSeenUtc, LastSeenUtc`.
3. **Get items** from `Etihad_Fleet` (Top 5000) — for in-memory matching.
4. **Apply to each** parsed row:
   - **Filter array** `Match` = existing items where `Title == item()?['Title']`.
   - **Condition** `length(Match) > 0`:
     - **Yes → Update item** (Id = `first(Match)?['ID']`)
     - **No  → Create item**
     - Fields: Title, Typecode, Model, ICAO24, Operator, Active, and `LastSeen = item()?['LastSeenUtc']`.

## Field notes vs. AeroDataBox
Provided: `Title` (reg), `Typecode` (ICAO, e.g. A35K/B789), `ICAO24` (hex), `Model`, `Operator`, `Active`.
Not available from ADS-B: `Serial`, `Delivered`, `AircraftId` (leave blank, or enrich later from the
free OpenSky CSV by matching on registration).

## Tune
- Frequency: edit the `cron` in the workflow (`0 */3 * * *`). More often = faster fill.
- Retirement window: `RETIRE_DAYS` in `sync.py` (default 30).
- Types swept: `TYPES` list in `sync.py` — add any new Etihad type code.
