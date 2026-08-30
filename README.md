# AI Resume Screener & Job Matcher

A full-stack tool that matches your resume against job descriptions using real sentence embeddings instead of keyword matching. Built as a portfolio project after getting frustrated with how shallow most "resume matcher" tools are.

## Demo

![Demo](Animation.gif)

## What it does

You paste in job descriptions you're applying to and upload your resume. The app computes a semantic similarity score between the two using a local embedding model, so it understands that "built REST APIs" and "developed backend services" mean roughly the same thing, which keyword matching completely misses. Each match also shows which skills overlap and which are missing.

## Tech stack

### Backend
| Tool | Purpose |
|------|---------|
| FastAPI | Async REST API framework |
| PostgreSQL + pgvector | Relational DB with vector storage |
| SQLModel (async) | ORM layer over SQLAlchemy 2.0 |
| sentence-transformers | all-MiniLM-L6-v2 model, 384-dim embeddings |
| PyTorch (CPU) | ML inference engine |
| PyMuPDF | PDF text extraction |
| PyJWT + passlib/bcrypt | JWT auth + password hashing |
| slowapi | Rate limiting (5/min login, 3/min register) |
| Alembic | Database schema migrations |

### Frontend
| Tool | Purpose |
|------|---------|
| React + TypeScript | UI framework |
| Vite | Dev server and build tool |
| Tailwind CSS v4 | Styling |
| shadcn/ui (base-ui) | Component library |
| axios | HTTP client |
| react-router-dom | Client-side routing |

### Infrastructure
Docker Compose runs three containers: frontend (Vite dev server), backend (FastAPI + uvicorn), and Postgres with the pgvector extension pre-built.

## Authentication

Auth uses httpOnly, Secure, SameSite=Strict cookies — not localStorage. On login, the backend sets an `access_token` cookie that's sent automatically with every request. The frontend never reads or stores the JWT directly, so XSS attacks can't steal it.

- `POST /auth/login` — sets the cookie and returns the token in the response body (for API clients)
- `POST /auth/logout` — clears the cookie
- `GET /auth/me` — returns the current user's profile from the cookie session

The backend also accepts `Authorization: Bearer <token>` headers as a fallback for programmatic API clients.

## How the matching works

1. When you upload a resume or add a job, the text goes to `all-MiniLM-L6-v2`, which produces a 384-dimensional embedding: a numerical representation of what the text means, not just which words it contains.
2. Vectors are stored in Postgres via the `pgvector` extension.
3. When you request a match, the backend computes cosine similarity between your resume's vector and every saved job's vector in Python (using numpy), not in SQL.
4. Raw cosine similarity for real resume/job pairs usually falls between about 0.20 and 0.70, so that range gets rescaled to 0-100% to produce a score that actually reads as intuitive.
5. Each match includes a keyword-overlap explanation showing matched and missing skills.

**Note:** pgvector is used for storage, but similarity computation happens in Python via `run_in_threadpool` to avoid blocking the async event loop. At the current scale (a handful of jobs per user), this is fast enough and avoids the complexity of ANN indexing.

## Database schema

```
users ──< resumes ──< matches
users ──< jobs    ──< matches
```

| Table | Key fields |
|-------|-----------|
| users | id, email, hashed_password, full_name, is_active |
| resumes | id, user_id (FK), filename, file_path, raw_text, embedding (vector 384), embedding_status |
| jobs | id, user_id (FK), title, company, description, requirements, embedding (vector 384), embedding_status |
| matches | id, resume_id (FK CASCADE), job_id (FK CASCADE), score, explanation |

`embedding_status` is `pending` → `ready` or `failed`, set by the background embedding task.

## API endpoints

**Auth**
- `POST /auth/register` — create account (3/min rate limit)
- `POST /auth/login` — log in, sets httpOnly cookie (5/min rate limit)
- `POST /auth/logout` — clears the cookie
- `GET /auth/me` — current user profile

**Resumes** (auth required)
- `POST /resumes/upload` — upload PDF resume (multipart, max 5MB, chunked size check, PDF magic-byte validation)
- `GET /resumes/` — list your resumes
- `GET /resumes/{id}` — get one resume
- `DELETE /resumes/{id}` — delete a resume (also removes the file from disk)

**Jobs** (auth required)
- `POST /jobs/` — add a job description
- `GET /jobs/` — list your saved jobs
- `GET /jobs/{id}` — get one job
- `DELETE /jobs/{id}` — delete a job

**Matching** (auth required)
- `POST /matches/compute?resume_id=XX` — score a resume against all your saved jobs

All resource endpoints enforce per-user ownership — returning 404 (not 403) for resources belonging to other users.

## Running locally

**Prerequisites:** Docker Desktop, Git

```bash
git clone https://github.com/rupinderkaur1904/resume-screener.git
cd resume-screener

cp backend/.env.example backend/.env
# edit backend/.env and set a real SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"

docker compose up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend API docs: http://localhost:9000/docs

First run takes a few minutes since Docker needs to pull the pgvector image and download the sentence-transformers model weights (~90MB). Both are cached in named volumes after that, so later starts are fast.

For local development without Docker, run the backend on port 8000:
```bash
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```
Then `cd frontend && npm run dev` starts Vite on port 5173 with a proxy to the backend.

## Database migrations

Alembic is configured for async use. The migration chain:
- `001` — adds `ON DELETE CASCADE` to match FK constraints
- `002` — adds `embedding_status` column to resumes and jobs

```bash
cd backend
alembic upgrade head     # apply all migrations
alembic downgrade -1     # revert last migration
alembic history          # show migration chain
```

On first startup, the app also runs `create_all()` to ensure tables exist. Alembic handles schema changes after that.

## Running tests

```bash
cd backend

# Unit tests (no DB needed)
pytest tests/test_new_features.py tests/test_pdf_parser.py tests/test_security.py tests/test_inference.py

# Migration tests (needs Docker Postgres on localhost:5432)
pytest tests/test_migration.py -v

# Authorization regression tests (needs Docker Postgres + running backend on :9000)
pytest tests/test_authorization.py -v

# All tests
pytest -v
```

Test coverage:
- Password validation (min length, bcrypt limits)
- Rate limiter enforcement (429 after threshold)
- PDF upload validation (extension, size, magic bytes, corrupt file handling)
- Keyword-overlap explanation logic (imports production function)
- CASCADE migration upgrade/downgrade
- Per-user authorization (User B cannot access User A's resources)
- JWT token creation/verification

## Key design decisions

**Jobs are private, not a shared pool.** You add a job because you personally found it (copied from LinkedIn, etc.), not because you're browsing a public listing. This mirrors how tools like Jobscan actually work.

**Embeddings are generated in the background.** Upload returns immediately; the embedding is computed asynchronously in a thread pool so users don't wait on ML inference during upload.

**Scores are rescaled, not raw.** Raw cosine similarity clusters in a narrow band for real resume/job pairs, so mapping that band to 0-100% produces something that actually feels meaningful.

**Explanations use keyword overlap.** Each match result shows which skills from the job description appear in the resume (matched) and which don't (missing), with stopwords filtered out. This complements the semantic score with concrete, actionable information.

## Project structure

```
resume-screener/
├── backend/
│   ├── app/
│   │   ├── api/           # routes and dependencies
│   │   ├── core/          # security helpers, rate limiter
│   │   ├── ml/            # model loader, inference functions
│   │   ├── models/        # SQLModel table definitions
│   │   ├── schemas/       # Pydantic request/response shapes
│   │   └── services/      # PDF parsing
│   ├── alembic/           # database migrations
│   ├── tests/             # unit + integration tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # shared axios client
│   │   ├── components/    # reusable UI components
│   │   ├── pages/         # Auth, Dashboard
│   │   └── lib/           # utilities and type definitions
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/     # CI for backend tests + frontend build
└── docker-compose.yml
```

## Limitations and what I'd do differently

The rescaling constants for the match score (0.20-0.70 mapped to 0-100%) were tuned by eyeballing similarity scores on a handful of real resume/job pairs, not from a proper labeled dataset. It works reasonably well in practice but isn't rigorous, and a better version would calibrate this against actual hiring outcomes or at least a bigger sample.

Similarity computation currently runs in Python via numpy rather than using pgvector's native `<=>` operator in SQL. At the current scale this is fine, but HNSW/IVFFlat indexing would be needed for production volumes.

## Author

**Rupinder Kaur**
BTech CSE, Thapar Institute of Engineering and Technology
[GitHub](https://github.com/rupinderkaur1904)
