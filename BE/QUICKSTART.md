# Quick start: what to install and how to run

## Option 1: Run with Docker (recommended if you have Docker)

### What you need
- **Docker** and **Docker Compose** (usually included with Docker Desktop on Windows).

Nothing else. No Python or PostgreSQL on your machine.

### Steps

1. **Open a terminal** in the project folder:
   ```bash
   cd E:\user\code\AI_copilet\BE
   ```

2. **Set your LLM provider and API key**  
   - **OpenAI:** `LLM_PROVIDER=openai` and set `OPENAI_API_KEY="sk-..."` in `.env.development`.
   - **Groq (free tier):** `LLM_PROVIDER=groq`, set `GROQ_API_KEY="..."` (get one at [console.groq.com](https://console.groq.com)), and optionally `DEFAULT_LLM_MODEL=llama-3.1-8b-instant` (or `llama-3.1-70b-versatile`, `mixtral-8x7b-32768`).

3. **Start the app and database** (builds images if needed):
   ```bash
   docker compose --env-file .env.development up -d --build db app
   ```
   On older setups you may need:
   ```bash
   docker-compose --env-file .env.development up -d --build db app
   ```

4. **Wait ~30 seconds** for the app to start and run migrations, then open:
   - **API docs (Swagger):** http://localhost:8000/docs  
   - **Health check:** http://localhost:8000/health  

5. **Optional – full stack** (app + DB + Prometheus + Grafana):
   ```bash
   set APP_ENV=development
   docker compose --env-file .env.development up -d --build
   ```
   Then: Prometheus http://localhost:9090, Grafana http://localhost:3000 (admin/admin).

### Stop
```bash
docker compose --env-file .env.development down
```

### Logs
```bash
docker compose --env-file .env.development logs -f app
```

---

## Check DB visually

### Option A: Adminer (browser, no install)

With the DB running in Docker, start Adminer:

```powershell
cd E:\user\code\AI_copilet\BE
docker compose --env-file .env.development up -d db adminer
```

Then open **http://localhost:8081** in your browser. Log in with the same values as in `.env.development`:

| Field    | Value       |
|----------|-------------|
| System   | PostgreSQL  |
| Server   | db          |
| Username | myuser      |
| Password | mypassword  |
| Database | mydb        |

**Important:** Type the database name exactly as `mydb` (no space before or after). A trailing space causes "database \"mydb \" does not exist".

You can browse tables (`user`, `session`, `thread`, etc.), run SQL, and export data.

### Option B: Desktop GUI (DBeaver, pgAdmin, TablePlus, etc.)

Connect with these settings (DB must be running; use `localhost` when the API runs on your machine):

| Setting  | Value      |
|----------|------------|
| Host     | localhost  |
| Port     | 5432       |
| Database | mydb       |
| User     | myuser     |
| Password | mypassword |

- **DBeaver:** https://dbeaver.io/ (free)
- **pgAdmin:** https://www.pgadmin.org/
- **TablePlus:** https://tableplus.com/ (free tier)

---

## Option 1b: Database in Docker, API run locally (good for development)

Use this when you want the **DB in Docker** but the **API on your machine** (easier to edit code and see logs).

### 1. Start only the database
From the project folder (`E:\user\code\AI_copilet\BE`):
```powershell
docker compose --env-file .env.development up -d db
```

### 2. Run the API in the terminal
The file `.env.development.local` sets `POSTGRES_HOST=localhost` so the local API connects to the DB in Docker.

```powershell
cd E:\user\code\AI_copilet\BE
$env:APP_ENV="development"
uv run uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000/docs

### 3. Stop the database when done
```powershell
docker compose --env-file .env.development stop db
```

---

## Option 2: Run without Docker (local Python + PostgreSQL)

### What you need
- **Python 3.13+**
- **PostgreSQL 16** with **pgvector** extension
- **uv** (recommended) or **pip**

### Steps

1. **Install uv** (optional but recommended):
   ```bash
   pip install uv
   ```

2. **Install dependencies**
   ```bash
   cd E:\user\code\AI_copilet\BE
   uv sync
   ```

3. **Configure environment**  
   Use `.env.development` but set database for **local** Postgres:
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=mydb
   POSTGRES_USER=myuser
   POSTGRES_PASSWORD=mypassword
   ```
   And set `OPENAI_API_KEY` and `JWT_SECRET_KEY` as above.

4. **Run the app**
   - With **Make** (if you have it, e.g. Git Bash / WSL):
     ```bash
     make dev
     ```
   - Or directly:
     ```bash
     set APP_ENV=development
     uv run uvicorn app.main:app --reload --port 8000
     ```

5. Open http://localhost:8000/docs

---

## Summary

| Goal              | Install              | Run |
|-------------------|----------------------|-----|
| Easiest (you have Docker) | Docker only          | `docker compose --env-file .env.development up -d --build db app` → http://localhost:8000/docs |
| **DB in Docker, API local** | Docker + Python 3.13+ + uv | `docker compose --env-file .env.development up -d db` then `uv run uvicorn app.main:app --reload --port 8000` |
| Local dev (no Docker) | Python 3.13+, PostgreSQL+pgvector, uv | `uv sync` then `uv run uvicorn app.main:app --reload --port 8000` (with `POSTGRES_HOST=localhost`) |

**Required before chat works:** set `OPENAI_API_KEY` in `.env.development`.
