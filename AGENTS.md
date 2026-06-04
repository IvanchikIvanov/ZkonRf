# AGENTS.md

## Cursor Cloud specific instructions

### Overview
This is a Telegram AI chatbot ("ZakonRFF") — a legal assistant for Russian Federation and CIS codexes. It uses Grok/OpenAI for LLM, OpenAI for embeddings/STT/TTS, PostgreSQL+pgvector for vector storage, Redis for caching, and SQLite for user data.

### Running the bot locally
```bash
source /workspace/.venv/bin/activate
python -m bot.main
```
Requires valid `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, and optionally `GROK_API_KEY` in `.env`.

### Infrastructure services
- **Redis**: runs in Docker container `zakonrff-redis` on port 6379. Start: `docker start zakonrff-redis` or `docker run -d --name zakonrff-redis -p 6379:6379 redis:7-alpine`
- **PostgreSQL 16 + pgvector**: installed locally via `postgresql-16-pgvector` package. Start: `sudo pg_ctlcluster 16 main start`. DB: `zakonrff`, user: `zakonrff`, password: `zakonrff`, port 5432.
- The pgvector HNSW index warns about >2000 dimensions (configured at 3072); this is expected and non-blocking — it falls back to sequential scan.

### Key gotchas
- `requirements.txt` has a conflict between `elevenlabs==2.27.0` (needs pydantic-core>=2.18.2) and the `pydantic>=2.4.1,<2.6` pin. Workaround: install elevenlabs with `--no-deps`, then install the rest. pip will resolve to newer pydantic which is compatible in practice.
- The bot requires Python 3.11 (venv at `/workspace/.venv`). `faiss-cpu==1.7.4` is not available for Python 3.12+.
- `VECTOR_BACKEND` defaults to `chroma` in code but `pgvector` is recommended (and configured in `.env`).
- The bot exits immediately with `InvalidToken` if `TELEGRAM_BOT_TOKEN` is not a real token — this is expected behavior.
- No test suite or formal linting config exists. Use `flake8 bot/ --max-line-length=120` for basic linting.
- Data directories: `data/codexes/`, `data/embeddings/`, `logs/` must exist.

### Lint
```bash
source /workspace/.venv/bin/activate
flake8 bot/ --max-line-length=120
```

### Environment variables
See `env.example` for full list. Key required secrets:
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `OPENAI_API_KEY` — for embeddings, STT, TTS, vision
- `GROK_API_KEY` — for primary LLM (optional, bot degrades without it)
