"""
Vercel Blob storage implementation for agent logs and file storage.

Provides file storage with graceful fallback for local development.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import quote_plus, unquote_plus

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from src.core.config import settings

logger = logging.getLogger(__name__)


class BlobMetrics:
    """Track blob storage performance metrics."""

    def __init__(self):
        self.uploads = 0
        self.downloads = 0
        self.deletes = 0
        self.errors = 0
        self.total_upload_time = 0
        self.total_download_time = 0
        self.total_delete_time = 0

    def record_upload(self, elapsed_ms: float):
        """Record upload operation."""
        self.uploads += 1
        self.total_upload_time += elapsed_ms

    def record_download(self, elapsed_ms: float):
        """Record download operation."""
        self.downloads += 1
        self.total_download_time += elapsed_ms

    def record_delete(self, elapsed_ms: float):
        """Record delete operation."""
        self.deletes += 1
        self.total_delete_time += elapsed_ms

    def record_error(self):
        """Record an error."""
        self.errors += 1

    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get blob storage metrics."""
        avg_upload_time = (self.total_upload_time / self.uploads) if self.uploads > 0 else 0
        avg_download_time = (self.total_download_time / self.downloads) if self.downloads > 0 else 0
        avg_delete_time = (self.total_delete_time / self.deletes) if self.deletes > 0 else 0

        return {
            "uploads": self.uploads,
            "downloads": self.downloads,
            "deletes": self.deletes,
            "errors": self.errors,
            "avg_upload_time_ms": round(avg_upload_time, 2),
            "avg_download_time_ms": round(avg_download_time, 2),
            "avg_delete_time_ms": round(avg_delete_time, 2),
        }


class BlobInterface(ABC):
    """Abstract base class for blob storage implementations."""

    @abstractmethod
    async def upload(self, path: str, content: Union[str, bytes], content_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload content to blob storage."""
        pass

    @abstractmethod
    async def download(self, path: str) -> Optional[bytes]:
        """Download content from blob storage."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete blob from storage."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if blob exists."""
        pass

    @abstractmethod
    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """List blobs with optional prefix."""
        pass

    @abstractmethod
    async def get_url(self, path: str, expires_in: Optional[int] = None) -> Optional[str]:
        """Get signed URL for blob access."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close blob storage connection."""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get storage performance metrics."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get storage configuration info."""
        pass


class VercelBlobStorage(BlobInterface):
    """
    Vercel Blob storage implementation with local fallback.

    Supports both Vercel environment and local development with graceful fallback.
    """

    def __init__(self):
        self.metrics = BlobMetrics()
        self._is_connected = False

    async def initialize(self) -> bool:
        """
        Initialize blob storage.

        For Vercel: Uses environment variables
        For local: Uses temporary directory with graceful fallback

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Check if we have Vercel Blob environment variables
            blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
            if blob_token:
                # Vercel environment detected
                self._storage_type = "vercel"
                self._blob_token = blob_token
                self._is_connected = True
                logger.info("✓ Vercel Blob storage initialized (Vercel environment)")
                return True
            else:
                # Local development - use filesystem fallback
                self._storage_type = "local"
                self._base_path = self._get_local_storage_path()
                self._is_connected = True
                logger.info(f"✓ Vercel Blob storage initialized (local fallback: {self._base_path})")
                return True

        except Exception as e:
            logger.error(f"✗ Vercel Blob storage initialization failed: {e}")
            return False

    def _get_local_storage_path(self) -> Path:
        """Get local storage path for blob files."""
        # Try to use configured path, otherwise use temp directory
        local_path = os.getenv("LOCAL_BLOB_PATH")
        if local_path:
            path = Path(local_path)
        else:
            path = Path(tempfile.gettempdir()) / "paygent_blobs"

        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def upload(self, path: str, content: Union[str, bytes], content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload content to blob storage.

        Args:
            path: Blob path
            content: Content to upload (string or bytes)
            content_type: MIME type of content (optional)

        Returns:
            Dict with upload result information
        """
        start_time = time.time()

        try:
            if not self._is_connected:
                return self._create_error_result("Storage not initialized")

            if self._storage_type == "vercel":
                return await self._upload_to_vercel(path, content, content_type)
            else:
                return await self._upload_to_local(path, content, content_type)

        except Exception as e:
            logger.error(f"Blob upload error for {path}: {e}")
            self.metrics.record_error()
            return self._create_error_result(str(e))
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_upload(elapsed)

    async def _upload_to_vercel(self, path: str, content: Union[str, bytes], content_type: Optional[str]) -> Dict[str, Any]:
        """Upload to Vercel Blob (placeholder - would need actual Vercel Blob API)."""
        # Note: Vercel Blob API would be used here in production
        # For now, we'll simulate the behavior or use local storage
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._upload_to_local(path, content, content_type)

    async def _upload_to_local(self, path: str, content: Union[str, bytes], content_type: Optional[str]) -> Dict[str, Any]:
        """Upload to local filesystem."""
        # Use synchronous file operations as fallback
        try:
            # Ensure directory exists
            full_path = self._base_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            else:
                content_bytes = content

            with open(full_path, 'wb') as f:
                f.write(content_bytes)

            # Create metadata
            metadata = {
                "path": path,
                "size": len(content_bytes),
                "content_type": content_type or "application/octet-stream",
                "storage_type": "local",
                "timestamp": time.time(),
                "success": True,
            }

            self.metrics.record_upload(0)  # Time already recorded in main method
            logger.debug(f"Blob uploaded locally: {path} ({len(content_bytes)} bytes)")
            return metadata

        except Exception as e:
            logger.error(f"Failed to upload blob {path}: {e}")
            return self._create_error_result(str(e))

    async def download(self, path: str) -> Optional[bytes]:
        """
        Download content from blob storage.

        Args:
            path: Blob path

        Returns:
            Content as bytes or None if not found
        """
        start_time = time.time()

        try:
            if not self._is_connected:
                return None

            if self._storage_type == "vercel":
                return await self._download_from_vercel(path)
            else:
                return await self._download_from_local(path)

        except Exception as e:
            logger.error(f"Blob download error for {path}: {e}")
            self.metrics.record_error()
            return None
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_download(elapsed)

    async def _download_from_vercel(self, path: str) -> Optional[bytes]:
        """Download from Vercel Blob (placeholder)."""
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._download_from_local(path)

    async def _download_from_local(self, path: str) -> Optional[bytes]:
        """Download from local filesystem."""
        full_path = self._base_path / path
        if not full_path.exists():
            return None

        try:
            with open(full_path, 'rb') as f:
                content = f.read()

            logger.debug(f"Blob downloaded locally: {path} ({len(content)} bytes)")
            return content

        except Exception as e:
            logger.error(f"Failed to download blob {path}: {e}")
            return None

    async def delete(self, path: str) -> bool:
        """
        Delete blob from storage.

        Args:
            path: Blob path

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()

        try:
            if not self._is_connected:
                return False

            if self._storage_type == "vercel":
                return await self._delete_from_vercel(path)
            else:
                return await self._delete_from_local(path)

        except Exception as e:
            logger.error(f"Blob delete error for {path}: {e}")
            self.metrics.record_error()
            return False
        finally:
            elapsed = (time.time() - start_time) * 1000
            self.metrics.record_delete(elapsed)

    async def _delete_from_vercel(self, path: str) -> bool:
        """Delete from Vercel Blob (placeholder)."""
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._delete_from_local(path)

    async def _delete_from_local(self, path: str) -> bool:
        """Delete from local filesystem."""
        full_path = self._base_path / path
        try:
            full_path.unlink()
            logger.debug(f"Blob deleted locally: {path}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {path}: {e}")
            return False

    async def exists(self, path: str) -> bool:
        """Check if blob exists."""
        try:
            if not self._is_connected:
                return False

            if self._storage_type == "vercel":
                return await self._exists_vercel(path)
            else:
                return await self._exists_local(path)

        except Exception as e:
            logger.error(f"Blob exists check error for {path}: {e}")
            return False

    async def _exists_vercel(self, path: str) -> bool:
        """Check existence in Vercel Blob (placeholder)."""
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._exists_local(path)

    async def _exists_local(self, path: str) -> bool:
        """Check existence in local filesystem."""
        full_path = self._base_path / path
        return full_path.exists()

    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """
        List blobs with optional prefix.

        Args:
            prefix: Optional prefix to filter results

        Returns:
            List of blob paths
        """
        try:
            if not self._is_connected:
                return []

            if self._storage_type == "vercel":
                return await self._list_vercel(prefix)
            else:
                return await self._list_local(prefix)

        except Exception as e:
            logger.error(f"Blob list error: {e}")
            self.metrics.record_error()
            return []

    async def _list_vercel(self, prefix: Optional[str]) -> List[str]:
        """List blobs in Vercel Blob (placeholder)."""
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._list_local(prefix)

    async def _list_local(self, prefix: Optional[str]) -> List[str]:
        """List blobs in local filesystem."""
        if not AIOFILES_AVAILABLE:
            return []

        search_path = self._base_path
        if prefix:
            search_path = self._base_path / prefix

        blob_paths = []
        if search_path.exists():
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    # Convert absolute path to relative path
                    rel_path = str(file_path.relative_to(self._base_path))
                    blob_paths.append(rel_path)

        return sorted(blob_paths)

    async def get_url(self, path: str, expires_in: Optional[int] = None) -> Optional[str]:
        """
        Get signed URL for blob access.

        Args:
            path: Blob path
            expires_in: Expiration time in seconds (optional)

        Returns:
            Signed URL or None if not supported
        """
        try:
            if not self._is_connected:
                return None

            if self._storage_type == "vercel":
                return await self._get_url_vercel(path, expires_in)
            else:
                # For local development, return file:// URL
                return await self._get_url_local(path)

        except Exception as e:
            logger.error(f"Blob URL generation error for {path}: {e}")
            return None

    async def _get_url_vercel(self, path: str, expires_in: Optional[int]) -> Optional[str]:
        """Get signed URL from Vercel Blob (placeholder)."""
        logger.warning("Vercel Blob API not implemented, using local storage fallback")
        return await self._get_url_local(path)

    async def _get_url_local(self, path: str) -> Optional[str]:
        """Get file:// URL for local blob."""
        full_path = self._base_path / path
        if full_path.exists():
            return f"file://{full_path.absolute()}"
        return None

    async def close(self) -> None:
        """Close blob storage connection."""
        # For local storage, no connection to close
        # For Vercel, would close any connections
        logger.info("Vercel Blob storage connection closed")

    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get blob storage metrics."""
        return self.metrics.get_metrics()

    def get_info(self) -> Dict[str, Any]:
        """Get blob storage configuration info."""
        info = {
            "type": "Vercel Blob",
            "connected": self._is_connected,
            "metrics": self.metrics.get_metrics(),
        }

        if self._is_connected:
            if self._storage_type == "vercel":
                info.update({
                    "storage_type": "vercel",
                    "blob_token_configured": bool(self._blob_token),
                    "local_path": None,
                })
            else:
                info.update({
                    "storage_type": "local",
                    "blob_token_configured": False,
                    "local_path": str(self._base_path),
                })
        else:
            info.update({
                "reason": "Not initialized",
            })

        return info

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create error result dictionary."""
        return {
            "success": False,
            "error": error_msg,
        }