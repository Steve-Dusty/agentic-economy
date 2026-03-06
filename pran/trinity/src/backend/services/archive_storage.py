"""
Abstract storage interface for log archives.

Supports pluggable backends with local-only default for sovereign deployments.
"""
import os
import shutil
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ArchiveStorage(ABC):
    """Abstract base class for archive storage backends."""

    @abstractmethod
    async def store_archive(
        self,
        source_path: Path,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Store an archive file.

        Args:
            source_path: Path to the archive file to store
            metadata: Optional metadata to attach to the archive

        Returns:
            Dict with storage info (path, size, etc.)

        Raises:
            Exception if storage fails
        """
        pass

    @abstractmethod
    def list_archives(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List stored archives.

        Args:
            prefix: Optional prefix to filter archives

        Returns:
            List of archive info dicts
        """
        pass

    @abstractmethod
    def delete_archive(self, archive_name: str):
        """
        Delete a stored archive.

        Args:
            archive_name: Name of the archive to delete
        """
        pass


class LocalArchiveStorage(ArchiveStorage):
    """
    Local filesystem storage for archives.

    Archives are moved to a specified local directory which can be:
    - A Docker volume for persistence
    - A mounted NAS/NFS share
    - A network-attached storage device
    """

    def __init__(self, archive_path: str = "/data/archives"):
        """
        Initialize local archive storage.

        Args:
            archive_path: Directory path for storing archives
        """
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local archive storage initialized: {self.archive_path}")

    async def store_archive(
        self,
        source_path: Path,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Move archive to local storage directory.

        Args:
            source_path: Path to the archive file
            metadata: Optional metadata (stored as JSON sidecar file)

        Returns:
            Dict with storage location and size

        Raises:
            Exception if move fails
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Archive file not found: {source_path}")

        try:
            dest_path = self.archive_path / source_path.name
            file_size = source_path.stat().st_size

            # Move file to archive directory (atomic on same filesystem)
            shutil.move(str(source_path), str(dest_path))

            logger.info(
                f"Archived {source_path.name} to local storage "
                f"({file_size / 1024 / 1024:.1f} MB)"
            )

            # Store metadata as sidecar JSON if provided
            if metadata:
                metadata_path = dest_path.with_suffix(dest_path.suffix + '.meta')
                import json
                metadata_path.write_text(json.dumps(metadata, indent=2))

            return {
                "storage_type": "local",
                "path": str(dest_path),
                "size": file_size,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            error_msg = f"Failed to store archive {source_path.name}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def list_archives(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        List archives in local storage.

        Args:
            prefix: Filter archives by filename prefix

        Returns:
            List of archive info dicts
        """
        try:
            archives = []
            pattern = f"{prefix}*.json.gz" if prefix else "*.json.gz"

            for archive_path in self.archive_path.glob(pattern):
                stat = archive_path.stat()

                # Load metadata if available
                metadata_path = archive_path.with_suffix(archive_path.suffix + '.meta')
                metadata = {}
                if metadata_path.exists():
                    import json
                    try:
                        metadata = json.loads(metadata_path.read_text())
                    except Exception as e:
                        logger.debug(f"Could not load metadata for {archive_path.name}: {e}")

                archives.append({
                    "name": archive_path.name,
                    "path": str(archive_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "metadata": metadata,
                })

            return sorted(archives, key=lambda x: x["modified"], reverse=True)

        except Exception as e:
            logger.error(f"Failed to list archives: {e}")
            raise

    def delete_archive(self, archive_name: str):
        """
        Delete an archive from local storage.

        Args:
            archive_name: Name of the archive file to delete
        """
        try:
            archive_path = self.archive_path / archive_name

            if not archive_path.exists():
                logger.warning(f"Archive not found for deletion: {archive_name}")
                return

            # Delete metadata sidecar if exists
            metadata_path = archive_path.with_suffix(archive_path.suffix + '.meta')
            if metadata_path.exists():
                metadata_path.unlink()

            # Delete archive file
            archive_path.unlink()
            logger.info(f"Deleted archive: {archive_name}")

        except Exception as e:
            logger.error(f"Failed to delete archive {archive_name}: {e}")
            raise


def get_archive_storage() -> ArchiveStorage:
    """
    Factory function to get the configured archive storage backend.

    Currently only returns LocalArchiveStorage for sovereign deployment.
    Future backends can be added here based on configuration.

    Returns:
        Configured ArchiveStorage instance
    """
    # Get archive path from environment
    archive_path = os.getenv("LOG_ARCHIVE_PATH", "/data/archives")

    logger.info("Using local archive storage (sovereign mode)")
    return LocalArchiveStorage(archive_path=archive_path)

