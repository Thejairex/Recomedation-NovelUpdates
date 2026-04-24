# AGENTS.md — NovelUpdates Recommender

## Essential Commands

### Setup
1. Copy `.env.example` → `.env` and fill `NU_SESSION_COOKIE` (from NovelUpdates logged-in cookie)
2. `docker-compose up --build` (starts API + PostgreSQL)
3. `docker-compose exec api alembic upgrade head` (apply migrations)

### Development
- Scrape reading list: `POST /scrape/my-novels`
- Scrape candidates: `POST /scrape/candidates`
- Generate recommendations: `POST /recommend`
- Get recommendations: `GET /recommend`
- Health check: `GET /health`
- View API logs: `docker-compose logs -f api`

## Critical Gotchas

### Environment
- **Never commit `.env`** (gitignored)
- `NU_SESSION_COOKIE` must be valid NovelUpdates session cookie (wordpress_logged_in_*)
- Cookie expires on logout; refresh if scraping fails with 401/403

### Scraping
- Rate limit: 1 second between requests (built-in)
- Retries: 3 attempts with exponential backoff on 429/5xx
- Reading list XML lacks slugs/tags; must scrape individual series pages
- Series Finder paginated; scrape one page at a time with delay

### Data Model
- User lists weights: `Best the Best`=3, `Reading/Completed/On Hold`=1, ignore `Plan to Read`/`Dropped`
- Recommendations exclude novels already in user's lists
- Top N recommendations configurable via `TOP_N_RECOMMENDATIONS` (default 20)

### Database
- Dev: SQLite (via SQLAlchemy async)
- Prod: PostgreSQL (configured in docker-compose)
- Migrations managed by Alembic; never use `create_tables()` in prod
- Tables: novels, tags, novel_tags, candidates, candidate_tags, recommendations

### Code Conventions
- Python 3.11+ with type hints
- Async/await for DB and HTTP operations
- Use `logging` module (never `print`)
- Scraping errors: log and continue (don't halt batch)

## Project Structure
```
main.py          # FastAPI endpoints
config.py        # Pydantic settings (.env)
database.py      # SQLAlchemy async engine/session
models.py        # ORM models
schemas.py       # Pydantic request/response schemas
scraper.py       # NovelUpdates scraping logic
recommender.py   # TF-IDF vectorization + cosine similarity
alembic/         # Database migrations
docker-compose.yml # API + PostgreSQL services
```

## Verified Workflow
```
1. docker-compose up --build
2. docker-compose exec api alembic upgrade head
3. POST /scrape/my-novels   # populates novels table
4. POST /scrape/candidates  # populates candidates table
5. POST /recommend          # generates & stores recommendations
6. GET /recommend           # returns top N recommendations
```