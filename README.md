# FastAPI + Supabase (getorder)

## Setup

1. Create `.env` from `.env.example`:
   - `SUPABASE_URL=https://ciuqkrpvqulgzukkwgxx.supabase.co`
   - `SUPABASE_KEY=<your publishable key>`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run API:
   - `uvicorn app.main:app --reload`

## Endpoints

- `GET /` - health check
- `GET /getorder?limit=100` - read rows from `public.convert_results` sorted by `created_at` descending
