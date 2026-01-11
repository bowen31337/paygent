# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server
uvicorn src.main:app --reload --port 8000

# Testing
pytest tests/                         # All tests (202 tests)
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests
pytest tests/ -k "test_name"          # Single test by name
pytest tests/ --cov=src               # With coverage

# Linting & Formatting
ruff check                            # Lint
ruff check --fix                      # Auto-fix
ruff format                           # Format
mypy src/                             # Type check

# Database migrations
alembic upgrade head                  # Apply migrations
alembic revision --autogenerate -m "desc"

# Frontend (Next.js in /app)
npm run dev                           # Dev server (port 3000)
npm run build                         # Production build
```

## Architecture

Paygent is a multi-agent payment orchestration platform for Cronos blockchain using the x402 protocol.

### Core Flow
```
User Command → FastAPI → PaygentAgent (deepagents) → Subagents → Services → Blockchain
```

### Key Directories
- `src/agents/` - AI agents using deepagents framework
  - `main_agent.py` - Primary orchestrating agent
  - `deepagents_executor.py` - Agent execution with filesystem backend
  - `*_subagent.py` - Specialized subagents (VVS trading, Moonlander perps, Delphi predictions)
- `src/api/routes/` - FastAPI endpoints (agent, payments, wallet, services, defi)
- `src/services/` - Business logic (X402PaymentService, WalletService, SessionService)
- `src/connectors/` - DeFi protocol integrations (vvs.py, moonlander.py, delphi.py)
- `src/tools/` - LangChain tools for agent operations
- `src/x402/` - x402 payment protocol with EIP-712 signatures
- `src/core/` - Config, database, cache, monitoring utilities

### Technology Stack
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (async), Pydantic
- **AI**: deepagents 0.2.7+, LangChain, Claude Sonnet 4 (primary), GPT-4 (fallback)
- **Blockchain**: Cronos EVM, ethers.js v6, x402 protocol
- **Database**: PostgreSQL (prod), SQLite (dev)
- **Cache**: Redis / Vercel KV

## Key Patterns

### Agent Development
- Always use `create_deep_agent()` from deepagents (never raw LangGraph StateGraph)
- Model string format: `"anthropic:claude-sonnet-4-20250514"`
- Custom base URLs supported via `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` env vars

### Tools
- Use LangChain `@tool` decorator for agent-accessible tools
- Tools registered via `register_tool()` method on agent instances

### Human-in-the-Loop
- Transactions > $100 USD require approval via ApprovalService
- Threshold configurable via `HITL_APPROVAL_THRESHOLD_USD`

### Configuration
- Settings in `src/core/config.py` (Pydantic BaseSettings)
- Cronos testnet: chain ID 338, RPC `https://evm-t3.cronos.org`
- Cronos mainnet: chain ID 25

## Testing Notes

- Tests use SQLite in-memory database and fakeredis
- Async tests use `@pytest.mark.asyncio` with `asyncio_mode = "auto"`
- Test fixtures in `tests/conftest.py`
