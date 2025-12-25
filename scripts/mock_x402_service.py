#!/usr/bin/env python
"""Mock service that returns HTTP 402 for x402 payment testing."""
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock x402 Service")


@app.get("/")
async def root():
    """Root endpoint that returns HTTP 402 with payment required header."""
    headers = {
        "Payment-Required": "x402; amount=0.10; token=USDC",
        "Content-Type": "application/json"
    }
    return JSONResponse(
        status_code=402,
        content={"error": "Payment Required", "message": "Please pay to access this service"},
        headers=headers
    )


@app.get("/free")
async def free_endpoint():
    """Free endpoint that doesn't require payment."""
    return {"message": "This endpoint is free", "data": {"value": 42}}


@app.get("/paid")
async def paid_endpoint():
    """Paid endpoint - returns 200 if Payment-Proof header is present."""
    return {"message": "Payment successful", "data": {"access": "granted"}}


if __name__ == "__main__":
    print("Starting mock x402 service on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
