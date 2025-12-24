# Paygent - AI-Powered Multi-Agent Payment Orchestration Platform

Paygent enables autonomous AI agents to discover, negotiate, and execute payments seamlessly across the Cronos ecosystem using the x402 protocol.

## Features

- **Natural Language Commands**: Execute payments using plain English
- **x402 Payment Protocol**: Automatic HTTP 402 payment handling with EIP-712 signatures
- **Service Discovery**: MCP-compatible service registry and marketplace
- **DeFi Integration**: VVS Finance, Moonlander, and Delphi protocol support
- **Human-in-the-Loop**: Configurable approval workflows for sensitive operations
- **Non-Custodial**: Users maintain control of their wallets

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the server
uvicorn src.main:app --reload
```

## Documentation

- API Documentation: `/docs` (Swagger UI)
- Alternative Docs: `/redoc` (ReDoc)

## License

MIT
