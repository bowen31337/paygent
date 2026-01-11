# Development Guide

This guide covers development setup, testing, and contribution guidelines for Paygent.

## Development Environment Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Cronos testnet wallet with test funds
- API keys for AI services (optional for basic functionality)

### Local Development

1. **Clone and Setup**
```bash
git clone https://github.com/your-org/paygent.git
cd paygent

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

2. **Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Configure for development
cat > .env << EOF
# Environment
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Database (SQLite for development)
DATABASE_URL=sqlite:///./paygent_dev.db

# Cache (Redis optional for development)
REDIS_URL=redis://localhost:6379

# AI Models (optional - will use mock responses if not configured)
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Blockchain (Cronos Testnet)
CRONOS_RPC_URL=https://evm-t3.cronos.org
CRONOS_CHAIN_ID=338
AGENT_WALLET_PRIVATE_KEY=your_private_key

# Services
X402_FACILITATOR_URL=https://x402-facilitator.cronos.org
CRYPTO_COM_API_KEY=your_crypto_com_key
CRYPTO_COM_MCP_URL=https://mcp.crypto.com
EOF
```

3. **Start Dependencies**
```bash
# Start Redis (optional)
docker run -d -p 6379:6379 redis:latest

# Or use fakeredis for testing (set USE_MOCK_REDIS=true in .env)
```

4. **Run Development Server**
```bash
# Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or with Docker Compose
docker-compose up -d
```

## Architecture Overview

### Core Components

1. **API Layer** (`src/api/`)
   - FastAPI endpoints for agent commands and payment operations
   - WebSocket support for streaming responses
   - Authentication and rate limiting middleware

2. **Agent Layer** (`src/agents/`)
   - Main AI agent with LangChain integration
   - Specialized subagents for different operations
   - Command parsing and execution orchestration

3. **Service Layer** (`src/services/`)
   - Business logic for payments, wallets, and sessions
   - Integration with external services and blockchain
   - Validation and security checks

4. **Data Layer** (`src/models/`, `src/core/`)
   - SQLAlchemy models for database entities
   - Database connection and session management
   - Redis cache integration

5. **Tools Layer** (`src/tools/`)
   - LangChain tools for agent operations
   - Payment, market data, and service discovery tools
   - Smart contract interaction tools

### Data Flow

```
User Command → Command Parser → Agent → Subagents → Services → Tools → External APIs/Blockchain
     ↓              ↓             ↓         ↓           ↓         ↓             ↓
   Input       Intent       Execution   Specialized  Business  Integration   External
  Validation   Analysis     Orchestration Operations  Logic     Layer       Services
```

## Testing Strategy

### Test Organization

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **End-to-End Tests** (`tests/e2e/`): Test complete user workflows

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # End-to-end tests

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run specific test
pytest tests/unit/test_agent.py::TestAgentExecute::test_execute_command_returns_200

# Run tests with verbose output
pytest tests/ -v

# Run tests in parallel
pytest tests/ -n auto
```

### Test Configuration

Tests are configured to use:
- SQLite in-memory database for isolation
- Mock external services for reliability
- Fakeredis for cache testing
- Factory Boy for test data generation

### Writing Tests

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_payment_endpoint(
    client: AsyncClient,
    db: AsyncSession,
    test_wallet: str
):
    """Test payment endpoint with real database."""
    response = await client.post("/payments/x402", json={
        "recipient": test_wallet,
        "amount": 10.0,
        "token": "USDC"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

## Code Style and Quality

### Code Formatting

```bash
# Format code with ruff
ruff format

# Check formatting
ruff format --check
```

### Linting

```bash
# Run linting
ruff check

# Fix auto-fixable issues
ruff check --fix
```

### Type Checking

```bash
# Run type checking
mypy src/

# Check specific files
mypy src/agents/main_agent.py
```

### Pre-commit Hooks

Install pre-commit hooks to automatically format and lint code:

```bash
pre-commit install
```

## Database Development

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade to previous migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Models

Models use SQLAlchemy with the following patterns:

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

class BaseModel:
    """Base model with common fields."""
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class Payment(Base, BaseModel):
    """Payment model."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    agent_wallet = Column(String, index=True)
    recipient = Column(String, index=True)
    amount = Column(Integer)  # Store as smallest unit
    token = Column(String)
    tx_hash = Column(String)
    status = Column(String, default="pending")
```

## Smart Contract Development

### Contract Structure

```
contracts/
├── AgentWallet.sol          # Main wallet contract
├── ServiceRegistry.sol      # Service discovery registry
├── interfaces/              # Interface definitions
│   ├── IERC20.sol
│   ├── IAgentWallet.sol
│   └── IServiceRegistry.sol
└── test/                    # Contract tests
    └── AgentWallet.t.sol
```

### Development Workflow

1. **Write Contract**
```solidity
// contracts/MyContract.sol
pragma solidity ^0.8.20;

contract MyContract {
    // Implementation
}
```

2. **Write Tests**
```solidity
// contracts/test/MyContract.t.sol
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/MyContract.sol";

contract MyContractTest is Test {
    MyContract public myContract;

    function setUp() public {
        myContract = new MyContract();
    }

    function testExample() public {
        // Test implementation
    }
}
```

3. **Run Tests**
```bash
# Run contract tests
forge test

# Run specific test
forge test -m "testExample"

# Run with coverage
forge coverage
```

4. **Build and Deploy**
```bash
# Build contracts
forge build

# Deploy to testnet
forge script script/Deploy.s.sol --rpc-url $CRONOS_RPC_URL --private-key $PRIVATE_KEY
```

## Docker Development

### Development Container

```bash
# Build development image
docker build -f Dockerfile.dev -t paygent:dev .

# Run with development configuration
docker run -p 8000:8000 \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/tests:/app/tests \
  -e DEBUG=true \
  -e DATABASE_URL=sqlite:///./paygent_dev.db \
  paygent:dev
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale web=3

# Stop services
docker-compose down
```

## Monitoring and Debugging

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("Payment executed", extra={
    "payment_id": payment_id,
    "amount": amount,
    "token": token,
    "wallet": wallet_address
})

# Debug logging (only in development)
logger.debug("Detailed debug info", extra={
    "raw_data": raw_data,
    "processed_data": processed_data
})
```

### Metrics

Custom metrics are automatically collected:

```python
from src.core.monitoring import metrics

# Record custom metric
metrics.record_payment_attempt(amount_usd, token_symbol)
metrics.record_agent_execution_time(agent_type, execution_time_ms)
```

### Debug Mode

```bash
# Enable debug mode
export DEBUG=true

# View detailed logs
uvicorn src.main:app --reload --log-level debug

# Profile performance
python -m cProfile -o profile.stats src/main.py
python -m pstats profile.stats
```

## Performance Optimization

### Database Optimization

- Use async database operations
- Implement proper indexing
- Use connection pooling
- Batch database operations when possible

### Cache Strategy

```python
from src.core.cache import cache_result

@cache_result(ttl=300)  # Cache for 5 minutes
async def get_market_price(symbol: str) -> float:
    # Expensive operation
    return await expensive_price_fetch(symbol)
```

### Agent Optimization

- Use appropriate model temperatures (0.1 for deterministic)
- Implement proper memory management
- Use subagents for specialized tasks
- Cache tool results when appropriate

## Security Best Practices

### Input Validation

```python
from pydantic import BaseModel, Field, validator

class PaymentRequest(BaseModel):
    recipient: str = Field(..., min_length=42, max_length=42)
    amount: float = Field(..., gt=0, lt=1000000)
    token: str = Field(..., min_length=2, max_length=10)

    @validator('recipient')
    def validate_address(cls, v):
        if not v.startswith('0x'):
            raise ValueError('Invalid address format')
        return v
```

### Smart Contract Security

- Use OpenZeppelin libraries
- Implement proper access control
- Add reentrancy guards
- Validate all inputs
- Use safe math operations

### API Security

- Implement rate limiting
- Use HTTPS in production
- Validate JWT tokens
- Sanitize all inputs
- Log security events

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
```bash
# Check database URL
echo $DATABASE_URL

# Test connection
python -c "import sqlalchemy; sqlalchemy.create_engine('$DATABASE_URL').connect()"
```

2. **Redis Connection Issues**
```bash
# Check Redis status
docker ps | grep redis

# Test Redis connection
redis-cli ping
```

3. **Smart Contract Deployment Failures**
```bash
# Check gas estimation
forge estimate-gas script/Deploy.s.sol

# Verify chain ID
forge chain-id --rpc-url $CRONOS_RPC_URL
```

4. **Agent Execution Timeouts**
```bash
# Check model API keys
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Test model connectivity
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages
```

### Debug Commands

```bash
# View application logs
tail -f logs/app.log

# Check system resources
docker stats

# Monitor database queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC;

# Check cache performance
redis-cli info stats
```

This development guide provides comprehensive information for contributing to Paygent. For specific questions, please refer to the code comments or create an issue in the repository.