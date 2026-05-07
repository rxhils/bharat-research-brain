# bharat-research-brain

Personal multi-agent research system for Indian equity markets (NSE/BSE). Ingests price, news, fundamentals, technicals, sectors, macro, and FII/DII flows. Outputs ranked watchlists and daily research reports into an Obsidian vault.

See [CLAUDE.md](CLAUDE.md) for the full project contract.

## Status

Phase 0 — Foundations.

## Quickstart

1. Copy `.env.example` to `.env` and fill in real values. Generate a Postgres password:

   ```
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Bring up the stack:

   ```
   docker compose up -d
   ```

3. Probe the health endpoint:

   ```
   curl http://localhost:8000/health
   ```

   Expected shape:

   ```json
   {"postgres":"ok","redis":"ok","ollama":"ok","overall":"healthy"}
   ```

## Architecture

To be filled in during Phase 1.
