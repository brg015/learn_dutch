# Streamlit App Deployment Plan (Hobby / Learning Project)

## Context & Goals

This project is a small Streamlit-based “study game” that I want to:
- Access from anywhere (phone + laptop)
- Keep costs at **free or near-zero**
- Learn **real deployment skills** (useful professionally)
- Keep security **simple but not reckless**
- Avoid 24/7 uptime requirements

The app:
- Is currently run locally via Streamlit
- Uses:
  - SQLite (local file) for session/study data
  - MongoDB Atlas (already hosted) for other content
- Has no sensitive data
- Is used by **me only (for now)**

---

## High-level Architecture (Target State)

**Frontend / App**
- Streamlit app
- Publicly accessible
- Hosted on **Hugging Face Spaces**
- Auto-sleeps when inactive

**Databases**
- MongoDB: unchanged (already hosted)
- SQL database:
  - Migrate from SQLite → **Postgres**
  - Hosted on **Neon (serverless Postgres, free tier)**

**Access Control**
- App is public, but gated by **simple PIN-based authentication**
- No user accounts
- No session persistence across browsers/devices required

**Backups**
- Nightly logical backups (`pg_dump`)
- Backups stored outside the DB provider
- Delayed recovery is acceptable (RPO ≈ 1 day)

---

## Key Design Decisions

### Why Hugging Face Spaces?
- Free tier supports Streamlit
- Auto-pauses after inactivity (acceptable)
- Wakes on access
- Good ecosystem recognition (“I’ve deployed on HF Spaces”)

### Why Neon (Postgres)?
- Free tier suitable for tiny DB (≈100 KB)
- Serverless + auto-suspend (fine for hobby usage)
- No manual “restart” required after inactivity
- Easy migration path from SQLite
- Good learning value (real Postgres)

### Why move away from SQLite?
- Hosted environments often have ephemeral disks
- SQLite concurrency limitations
- Postgres is closer to production setups
- Easier to back up and query externally

---

## Authentication Strategy

**Requirements**
- Extremely simple
- Low friction
- No sensitive data to protect
- Main goal: avoid random internet access

**Chosen approach**
- Single shared **PIN code** (e.g. 4–6 digits)
- PIN stored in environment variable (`APP_PIN`)
- User enters PIN once per session
- Session stored in `st.session_state`

**Explicit non-goals**
- No OAuth
- No user accounts
- No password reset flows
- No strong security guarantees

---

## Database Migration Plan (SQLite → Postgres)

### Current state
- Uses Python `sqlite3`
- Writes a row after each study question
- Write frequency: ~6 writes/minute
- DB size: ~100 KB

### Target state
- Use **Postgres via SQLAlchemy**
- Connection string via `DATABASE_URL` env var
- Schema defined in code (SQLAlchemy models)

### Migration steps
1. Define SQLAlchemy models matching current SQLite schema
2. Create Postgres schema on Neon
3. One-off migration script:
   - Read from SQLite
   - Insert into Postgres
4. Remove SQLite usage from app runtime

---

## Backup Strategy

### Requirements
- Nightly backups
- Data loss of <24h acceptable
- Simple and inspectable
- No production-grade HA needed

### Proposed solution
- Nightly `pg_dump`
- Dump format: plain SQL
- Storage:
  - Initially: local machine (manual pull)
  - Later: GitHub private repo or object storage

### Notes
- Backups may be run manually at first
- Automation can be added later (cron / GitHub Actions)

---

## Environment Variables (Target)

The app will rely on the following env vars:

- `DATABASE_URL`
  - Postgres connection string from Neon
- `APP_PIN`
  - Simple numeric PIN for app access
- `MONGODB_URI`
  - Already used, unchanged

All secrets stored in:
- Hugging Face Spaces → Secrets
- Local `.env` file (gitignored)

---

## Deployment Steps (High-level)

1. Prepare repo for deployment
   - Ensure `requirements.txt` is complete
   - Ensure Streamlit entrypoint is clear

2. Create Neon Postgres project
   - Copy connection string
   - Set `DATABASE_URL`

3. Refactor DB layer
   - Replace `sqlite3` with SQLAlchemy + Postgres
   - Add migration script

4. Add simple PIN authentication
   - Streamlit UI gate
   - Session-based unlock

5. Deploy to Hugging Face Spaces
   - Link GitHub repo
   - Add secrets
   - Verify app wakes from sleep correctly

6. Add backup documentation + script
   - Manual first
   - Automation later

---

## Out of Scope (For Now)

- Public multi-user support
- User accounts
- Analytics dashboards hosted online
- ML pipelines running in the cloud
- CI/CD pipelines
- Dockerization

---

## Success Criteria

- App is accessible from phone/laptop anywhere
- No local machine required to be running
- DB survives restarts and sleeps
- Writes work reliably
- Backup can be restored if needed
- Total monthly cost: **€0**

---

## Notes for Future Expansion

- Add rate limiting if app becomes public
- Replace PIN auth with proper auth if users are added
- Add DB read replica / analytics DB if ML usage grows
- Containerize app (Docker) as a learning exercise
