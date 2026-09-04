# AI Code Reviewer

An AI-powered multi-agent code review system.

## Features
- GitHub Webhook Integration
- Multi-Agent Review via LangGraph
- Multi-LLM Support (Google Gemini by default)

## Quick Start
```bash
cp .env.example .env
# Edit .env and add GITHUB_TOKEN and GOOGLE_API_KEY
docker-compose up -d
```

## Architecture
```
GitHub -> Webhook -> FastAPI -> Celery Worker -> LangGraph Agents -> LLM -> GitHub PR Comment
```

## Configuration Reference
Check `.env.example` for all configurable environment variables.
- `LLM_PROVIDER`: Set to `google`, `openai`, `anthropic`, or `ollama`. Default is `google`.
- `AUTO_FIX_ENABLED`: Controls if autofix suggestions are enabled.

## Agent Descriptions
- Uses LangGraph to orchestrate multiple LLM agents (supervisor, code quality, security).

## API Endpoints
- `POST /webhook`: GitHub webhooks endpoint
