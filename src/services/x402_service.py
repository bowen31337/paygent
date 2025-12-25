"""
X402 payment service.

This service handles HTTP 402 payment protocol operations including
payment execution, EIP-712 signature generation, and facilitator integration.
"""

import asyncio
import json
import logging
from typing import Any

from httpx import AsyncClient, Response
from httpx import TimeoutException as HttpxTimeoutException

from src.core.config import settings
from src.core.errors import create_safe_error_message
from src.services.metrics_service import metrics_collector

logger = logging.getLogger(__name__)


class X402PaymentService:
    """Service for x402 payment protocol operations."""

    def __init__(self):
        """Initialize the X402 payment service."""
        self.facilitator_url = settings.x402_facilitator_url
        self.client = AsyncClient(timeout=30.0)
        self.retry_attempts = 3
        self.retry_delay = 1.0

    def _safe_parse_json(self, response: Response) -> dict[str, Any] | None:
        """
        Safely parse JSON from HTTP response with error handling.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            if not response.content:
                logger.warning("Empty response body received")
                return None

            data = response.json()
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in response: {e}")
            logger.debug(f"Response content (first 200 chars): {response.text[:200]}")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse response JSON: {e}")
            return None

    async def execute_payment(
        self,
        service_url: str,
        amount: float,
        token: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute an x402 payment flow.

        Args:
            service_url: URL of the service to pay
            amount: Amount to pay
            token: Token symbol
            description: Optional payment description

        Returns:
            Dict containing payment execution result
        """
        try:
            logger.info(
                f"Starting x402 payment: {amount} {token} to {service_url}"
            )

            # Step 1: Make initial request to service
            payment_result = await self._make_payment_request(
                service_url=service_url,
                amount=amount,
                token=token,
                description=description,
            )

            if payment_result["success"]:
                # Record successful payment metric
                metrics_collector.record_payment(amount_usd=amount, success=True)
                return {
                    "success": True,
                    "payment_id": payment_result.get("payment_id"),
                    "tx_hash": payment_result.get("tx_hash"),
                    "status": payment_result.get("status"),
                    "message": payment_result.get("message", "Payment executed successfully"),
                }
            else:
                # Record failed payment metric
                metrics_collector.record_payment(amount_usd=amount, success=False)
                return {
                    "success": False,
                    "error": payment_result.get("error"),
                    "message": payment_result.get("message", "Payment execution failed"),
                }

        except HttpxTimeoutException as e:
            logger.error(f"x402 payment timeout: {e}")
            # Record failed payment metric
            metrics_collector.record_payment(amount_usd=amount, success=False)
            return {
                "success": False,
                "error": "timeout",
                "message": "The payment service is taking too long to respond. This could be due to network issues or high service load. Please try again.",
            }
        except Exception as e:
            logger.error(f"x402 payment execution failed: {e}")
            # Record failed payment metric
            metrics_collector.record_payment(amount_usd=amount, success=False)
            return {
                "success": False,
                "error": str(e),
                "message": create_safe_error_message(e),
            }

    async def _make_payment_request(
        self,
        service_url: str,
        amount: float,
        token: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Make a payment request following x402 protocol.

        Args:
            service_url: URL of the service to pay
            amount: Amount to pay
            token: Token symbol
            description: Optional payment description

        Returns:
            Dict containing payment result
        """
        try:
            # Retry logic for payment requests
            for attempt in range(self.retry_attempts):
                try:
                    # Step 1: Initial request to service
                    logger.info(f"Attempt {attempt + 1}: Making request to {service_url}")

                    response = await self.client.get(
                        service_url,
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "Paygent/1.0",
                        },
                    )

                    # Step 2: Handle HTTP 402 response
                    if response.status_code == 402:
                        payment_result = await self._handle_402_response(
                            response=response,
                            service_url=service_url,
                            amount=amount,
                            token=token,
                            description=description,
                        )

                        if payment_result["success"]:
                            return payment_result
                        else:
                            continue  # Retry if payment failed

                    elif response.status_code == 200:
                        # No payment required - safely parse response
                        response_data = self._safe_parse_json(response)
                        if response_data is None and response.content:
                            # JSON parsing failed but there's content
                            logger.warning("Response data could not be parsed as JSON")
                            return {
                                "success": False,
                                "error": "invalid_response_format",
                                "message": "Service returned an invalid response format. Please contact support.",
                            }

                        return {
                            "success": True,
                            "payment_id": None,
                            "tx_hash": None,
                            "status": "no_payment_required",
                            "message": "Service does not require payment",
                            "data": response_data,
                        }

                    elif response.status_code == 429:
                        # Rate limit exceeded
                        retry_after = response.headers.get("Retry-After", "60")
                        return {
                            "success": False,
                            "error": "rate_limited",
                            "message": f"Service rate limit exceeded. Please try again in {retry_after} seconds.",
                        }

                    elif response.status_code >= 500:
                        # Server errors - these might be temporary
                        error_data = self._safe_parse_json(response)
                        error_msg = error_data.get("error", "Service error") if error_data else "Service error"
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "message": f"Service is currently unavailable ({response.status_code}). Please try again later. Error: {error_msg}",
                        }

                    else:
                        # Other HTTP errors
                        error_data = self._safe_parse_json(response)
                        error_msg = error_data.get("error", "Unknown error") if error_data else "Unknown error"
                        return {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "message": f"Service returned error: {response.status_code} - {error_msg}",
                        }

                except HttpxTimeoutException as e:
                    # Handle timeout specifically with user-friendly message
                    logger.warning(f"Timeout on attempt {attempt + 1}/{self.retry_attempts}: {e}")
                    if attempt < self.retry_attempts - 1:
                        # Exponential backoff for retries
                        backoff_time = self.retry_delay * (2**attempt)
                        logger.info(f"Retrying in {backoff_time}s...")
                        await asyncio.sleep(backoff_time)
                    else:
                        # Final attempt failed - return timeout error
                        return {
                            "success": False,
                            "error": "timeout",
                            "message": "Service is taking too long to respond. Please try again later. The service may be experiencing high load or temporary network issues.",
                        }
                except Exception as e:
                    # Handle other exceptions
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))  # Exponential backoff
                    else:
                        raise

            return {
                "success": False,
                "error": "max_retries_exceeded",
                "message": f"Payment failed after {self.retry_attempts} attempts",
            }

        except Exception as e:
            logger.error(f"Payment request failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Payment request failed: {str(e)}",
            }

    async def _handle_402_response(
        self,
        response: Response,
        service_url: str,
        amount: float,
        token: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle HTTP 402 response by executing payment via facilitator.

        Args:
            response: HTTP 402 response from service
            service_url: URL of the service to pay
            amount: Amount to pay
            token: Token symbol
            description: Optional payment description

        Returns:
            Dict containing payment execution result
        """
        try:
            # Parse 402 response headers
            payment_required_header = response.headers.get("Payment-Required")
            if not payment_required_header:
                return {
                    "success": False,
                    "error": "missing_payment_required_header",
                    "message": "Service did not provide Payment-Required header",
                }

            # Parse payment required header (format: "x402; amount=0.10; token=USDC")
            payment_info = self._parse_payment_required_header(payment_required_header)

            # Verify payment details
            if payment_info.get("amount") != str(amount):
                return {
                    "success": False,
                    "error": "amount_mismatch",
                    "message": f"Requested amount {amount} does not match service requirement {payment_info.get('amount')}",
                }

            if payment_info.get("token") != token:
                return {
                    "success": False,
                    "error": "token_mismatch",
                    "message": f"Requested token {token} does not match service requirement {payment_info.get('token')}",
                }

            # Step 3: Generate EIP-712 signature
            signature_result = await self._generate_eip712_signature(
                service_url=service_url,
                amount=amount,
                token=token,
                description=description,
            )

            if not signature_result["success"]:
                return signature_result

            # Step 4: Submit payment to facilitator
            facilitator_result = await self._submit_to_facilitator(
                service_url=service_url,
                amount=amount,
                token=token,
                signature=signature_result["signature"],
                description=description,
            )

            if not facilitator_result["success"]:
                return facilitator_result

            # Step 5: Retry original request with payment proof
            final_response = await self.client.get(
                service_url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Paygent/1.0",
                    "Payment-Proof": facilitator_result["payment_proof"],
                },
            )

            if final_response.status_code == 200:
                return {
                    "success": True,
                    "payment_id": facilitator_result["payment_id"],
                    "tx_hash": facilitator_result["tx_hash"],
                    "status": "completed",
                    "message": "Payment completed successfully",
                    "data": final_response.json() if final_response.content else None,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {final_response.status_code}",
                    "message": "Service still requires payment after facilitator submission",
                }

        except Exception as e:
            logger.error(f"402 response handling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"402 response handling failed: {str(e)}",
            }

    def _parse_payment_required_header(self, header: str) -> dict[str, str]:
        """
        Parse Payment-Required header.

        Args:
            header: Payment-Required header value

        Returns:
            Dict containing parsed payment information
        """
        try:
            parts = header.split(";")
            result = {}

            for part in parts:
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    result[key.strip()] = value.strip()
                elif part:  # Handle keys without values (e.g., "x402")
                    result[part] = ""

            return result

        except Exception as e:
            logger.error(f"Failed to parse Payment-Required header: {e}")
            return {}

    async def _generate_eip712_signature(
        self,
        service_url: str,
        amount: float,
        token: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate EIP-712 signature for payment authorization.

        Args:
            service_url: URL of the service
            amount: Payment amount
            token: Token symbol
            description: Optional payment description

        Returns:
            Dict containing signature result
        """
        try:
            from src.x402.signature import get_signature_generator

            # Get signature generator
            generator = get_signature_generator()

            # Get wallet address (mock for development)
            wallet_address = "0xFCAd0B19bB29D4674531d6f115237E16AfCE377c"  # Mock checksum address

            # Create payment data
            payment_data = generator.create_payment_data(
                service_url=service_url,
                amount=amount,
                token=token,
                wallet_address=wallet_address,
                description=description,
            )

            # Sign payment
            signature_result = generator.sign_payment(payment_data)

            if signature_result["success"]:
                return {
                    "success": True,
                    "signature": signature_result["signature"],
                    "signer": signature_result["signer"],
                    "message": "EIP-712 signature generated successfully",
                }
            else:
                return signature_result

        except Exception as e:
            logger.error(f"EIP-712 signature generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"EIP-712 signature generation failed: {str(e)}",
            }

    async def _submit_to_facilitator(
        self,
        service_url: str,
        amount: float,
        token: str,
        signature: dict[str, Any],
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Submit payment to x402 facilitator for settlement.

        Args:
            service_url: URL of the service
            amount: Payment amount
            token: Token symbol
            signature: EIP-712 signature
            description: Optional payment description

        Returns:
            Dict containing facilitator submission result
        """
        try:
            # Use mock facilitator if no real one is configured
            if not self.facilitator_url or settings.debug:
                logger.info("Using mock x402 facilitator")
                from src.x402.mock_facilitator import get_mock_facilitator

                mock_facilitator = get_mock_facilitator()
                result = await mock_facilitator.submit_payment(
                    service_url=service_url,
                    amount=amount,
                    token=token,
                    signature=signature,
                    description=description or "",
                )

                if "paymentId" in result:
                    return {
                        "success": True,
                        "payment_id": result["paymentId"],
                        "tx_hash": result.get("txHash"),
                        "payment_proof": result.get("paymentProof"),
                        "message": "Payment submitted to mock facilitator successfully",
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error"),
                        "message": result.get("message", "Mock facilitator submission failed"),
                    }

            # Prepare facilitator request
            facilitator_payload = {
                "serviceUrl": service_url,
                "amount": amount,
                "token": token,
                "description": description or "",
                "signature": signature,
                "timestamp": 1234567890,
            }

            # Submit to facilitator
            facilitator_response = await self.client.post(
                f"{self.facilitator_url}/submit-payment",
                json=facilitator_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Paygent/1.0",
                },
            )

            if facilitator_response.status_code == 200:
                response_data = facilitator_response.json()

                return {
                    "success": True,
                    "payment_id": response_data.get("paymentId"),
                    "tx_hash": response_data.get("txHash"),
                    "payment_proof": response_data.get("paymentProof"),
                    "message": "Payment submitted to facilitator successfully",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {facilitator_response.status_code}",
                    "message": f"Facilitator returned error: {facilitator_response.status_code}",
                }

        except Exception as e:
            logger.error(f"Facilitator submission failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Facilitator submission failed: {str(e)}",
            }

    async def verify_payment(self, payment_id: str) -> dict[str, Any]:
        """
        Verify payment status with facilitator.

        Args:
            payment_id: Payment ID to verify

        Returns:
            Dict containing verification result
        """
        try:
            if not self.facilitator_url:
                return {
                    "success": False,
                    "error": "no_facilitator_configured",
                    "message": "No x402 facilitator URL configured",
                }

            # Verify payment with facilitator
            verify_response = await self.client.get(
                f"{self.facilitator_url}/verify-payment/{payment_id}",
                headers={
                    "User-Agent": "Paygent/1.0",
                },
            )

            if verify_response.status_code == 200:
                response_data = verify_response.json()

                return {
                    "success": True,
                    "payment_id": payment_id,
                    "status": response_data.get("status"),
                    "tx_hash": response_data.get("txHash"),
                    "verified": response_data.get("verified", False),
                    "message": "Payment verification completed",
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {verify_response.status_code}",
                    "message": f"Facilitator returned error: {verify_response.status_code}",
                }

        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Payment verification failed: {str(e)}",
            }
