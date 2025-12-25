# Paygent - AI-Powered Multi-Agent Payment Orchestration Platform

**Transforming AI agent payments with natural language commands and the x402 protocol on Cronos.**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern%20Web%20Framework-green.svg)](https://fastapi.tiangolo.com)
[![Cronos](https://img.shields.io/badge/Cronos-EVM%20Compatible-orange.svg)](https://cronos.org)
[![x402](https://img.shields.io/badge/Protocol-x402%20Payments-yellow.svg)](https://github.com/ethereum/EIPs/blob/master/EIPS/eip-402.md)

Paygent enables autonomous AI agents to discover, negotiate, and execute payments seamlessly across the Cronos ecosystem using the x402 protocol. Built with modern Python, FastAPI, and LangChain, it provides a robust foundation for AI-driven payment orchestration.

## 🚀 Key Features

### Core Capabilities
- **Natural Language Commands**: Execute payments using plain English
- **x402 Payment Protocol**: Automatic HTTP 402 payment handling with EIP-712 signatures
- **Service Discovery**: MCP-compatible service registry and marketplace
- **Multi-Agent Architecture**: Specialized subagents for different tasks (VVS trading, Moonlander, Delphi predictions)
- **Human-in-the-Loop**: Configurable approval workflows for sensitive operations
- **Non-Custodial**: Users maintain control of their wallets

### Advanced Features
- **DeFi Integration**: VVS Finance, Moonlander, and Delphi protocol support
- **Smart Contract Security**: ReentrancyGuard, SafeERC20, and comprehensive security patterns
- **Real-time Market Data**: Crypto.com Market Data MCP Server integration
- **Comprehensive Monitoring**: Prometheus metrics and structured logging
- **Production-Ready**: Docker, Vercel deployment, and CI/CD workflows

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Input    │    │   AI Agent      │    │  Payment Flow   │
│  (Natural Lang) │───▶│   (Claude/     │───▶│  (x402 + EVM)   │
│                 │    │   GPT-4)        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Subagents      │
                       │  (VVS, Moonl,  │
                       │   Delphi, etc.) │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Service Disc.  │
                       │  (MCP Registry) │
                       └─────────────────┘
```

### Technology Stack

**Backend:**
- **Framework**: FastAPI with async/await patterns
- **AI/ML**: LangChain, Claude Sonnet 4, GPT-4 with fallback
- **Database**: PostgreSQL (production) + SQLite (development)
- **Cache**: Redis + Vercel KV
- **Blockchain**: Cronos EVM, x402 protocol
- **Web3**: ethers.js v6, EIP-712 signatures

**Infrastructure:**
- **Container**: Docker with multi-stage builds
- **Deployment**: Vercel Serverless Functions
- **Monitoring**: Prometheus, structured logging
- **Security**: JWT auth, rate limiting, CORS

## 📦 Installation

### Prerequisites
- Python 3.12+
- Docker (optional)
- Cronos wallet with testnet funds

### Local Development

1. **Clone and Setup**
```bash
git clone https://github.com/your-org/paygent.git
cd paygent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

2. **Environment Configuration**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
vim .env
```

3. **Required Environment Variables**
```bash
# Core Configuration
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# AI Models
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
DEFAULT_MODEL=claude-sonnet-4-20250514

# Blockchain
CRONOS_RPC_URL=https://evm-t3.cronos.org
CRONOS_CHAIN_ID=338
AGENT_WALLET_PRIVATE_KEY=your_private_key

# Database
POSTGRES_URL=postgresql://user:pass@localhost:5432/paygent
DATABASE_URL=sqlite:///./paygent.db

# Cache
REDIS_URL=redis://localhost:6379
KV_URL=your_vercel_kv_url

# Services
X402_FACILITATOR_URL=https://x402-facilitator.cronos.org
CRYPTO_COM_API_KEY=your_crypto_com_key
CRYPTO_COM_MCP_URL=https://mcp.crypto.com
```

4. **Run the Application**
```bash
# Start the server
uvicorn src.main:app --reload

# Or with Docker
docker-compose up -d
```

## 🎯 Usage Examples

### Basic Payment Commands
```bash
# Simple payment
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Pay 0.10 USDC to access the market data API"}'

# Check balance
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Check my USDC balance"}'

# Transfer tokens
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Send 100 USDC to 0xRecipientAddress"}'
```

### DeFi Operations
```bash
# VVS Finance Swap
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Swap 100 USDC for CRO on VVS Finance"}'

# Moonlander Trading
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Open a 10x long position on BTC/USDC on Moonlander"}'

# Delphi Predictions
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Place a bet on Bitcoin exceeding $50,000"}'
```

### Service Discovery
```bash
# Discover services
curl -X POST "http://localhost:8000/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{"command": "Find market data services"}'

# Check service status
curl -X GET "http://localhost:8000/mcp/discover"
```

## 🔧 API Reference

### Agent Endpoints

#### Execute Command
```http
POST /agent/execute
```

Execute natural language commands with optional budget limits.

**Request:**
```json
{
  "command": "Pay 0.10 USDC to access the market data API",
  "budget_limit_usd": 100.0
}
```

**Response:**
```json
{
  "success": true,
  "result": "Payment executed successfully",
  "session_id": "uuid",
  "total_cost_usd": 0.10
}
```

#### Stream Response
```http
POST /agent/execute/stream
```

Execute commands with streaming responses for long-running operations.

#### Get Session
```http
GET /agent/sessions/{session_id}
```

Retrieve session information and execution history.

### Payment Endpoints

#### x402 Payment
```http
POST /payments/x402
```

Execute HTTP 402 payments with EIP-712 signatures.

#### Check Payment Status
```http
GET /payments/{payment_id}/status
```

Check the status of a payment.

### Service Discovery

#### List Services
```http
GET /mcp/discover
```

Discover available MCP-compatible services.

#### Service Details
```http
GET /mcp/services/{service_id}
```

Get detailed information about a specific service.

## 🏗️ Development

### Project Structure
```
paygent/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── agents/           # AI agent implementations
│   ├── core/             # Core utilities (config, database, cache)
│   ├── models/           # Database models
│   ├── services/         # Business logic services
│   ├── tools/            # LangChain tools
│   └── contracts/        # Smart contract artifacts
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── contracts/            # Solidity smart contracts
├── scripts/              # Deployment and utility scripts
└── docs/                 # Documentation
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_agent.py::TestAgentExecute::test_execute_command_returns_200
```

### Code Style
```bash
# Format code
ruff format

# Run linting
ruff check

# Type checking
mypy src/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## 🚀 Deployment

### Vercel Deployment
1. Push to main branch
2. Vercel automatically deploys
3. Environment variables configured in Vercel dashboard

### Docker Deployment
```bash
# Build image
docker build -t paygent .

# Run container
docker run -p 8000:8000 paygent

# With environment variables
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e CRONOS_RPC_URL=https://evm-t3.cronos.org \
  paygent
```

## 🔒 Security

### Smart Contract Security
- **ReentrancyGuard**: Prevents reentrancy attacks
- **SafeERC20**: Safe token transfers
- **Access Control**: Restricted admin functions
- **Input Validation**: Comprehensive parameter validation

### API Security
- **Rate Limiting**: Prevents abuse
- **CORS**: Controlled cross-origin requests
- **JWT Authentication**: Secure session management
- **Input Validation**: Pydantic models with validation

### Best Practices
- Non-custodial wallet management
- Human-in-the-loop for sensitive operations
- Comprehensive logging and monitoring
- Regular security audits

## 🤖 AI Agent Configuration

### Model Selection
```python
# Primary model (Claude Sonnet 4)
DEFAULT_MODEL = "anthropic/claude-sonnet-4"

# Fallback model (GPT-4)
FALLBACK_MODEL = "openai/gpt-4"
```

### Agent Behavior
- **Temperature**: 0.1 (deterministic responses)
- **Max Tokens**: 4000 (sufficient for complex operations)
- **Memory**: Conversation buffer with session persistence
- **Tools**: Specialized tools for payments, trading, and market data

### Subagents
- **VVS Trader**: Handles VVS Finance swaps
- **Moonlander Trader**: Manages perpetual trading
- **Delphi Predictor**: Executes prediction market operations

## 📊 Monitoring & Observability

### Metrics
- Prometheus endpoint at `/metrics`
- Custom metrics for payments, agent usage, and performance
- Request/response times and error rates

### Logging
- Structured JSON logging
- Log levels configurable via environment
- Request tracing and correlation IDs

### Health Checks
- Application health at `/health`
- Database connectivity checks
- External service availability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

### Code Review Guidelines
- All PRs require review
- Tests must pass
- Documentation updates required for new features
- Follow existing code style

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Cronos Ecosystem**: For providing the blockchain infrastructure
- **LangChain**: For enabling powerful AI agent capabilities
- **FastAPI**: For modern, fast web framework
- **Community**: For feedback and contributions

## 🔗 Resources

- [Cronos Documentation](https://docs.cronos.org)
- [x402 Protocol](https://github.com/ethereum/EIPs/blob/master/EIPS/eip-402.md)
- [LangChain Documentation](https://python.langchain.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

---

**Built with ❤️ for the Cronos ecosystem**
