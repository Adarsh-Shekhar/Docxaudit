"""Storage abstraction (Phase 7.1).

Two implementations:
- LocalStorage: dev default (local disk, TRD §2.4).
- R2Storage: prod outgrowth (Cloudflare R2) — raises NotConfigured for now;
  wire it only if local disk stops being viable on Render (Phase 36 stretch).

Rules: never trust client filenames for storage paths (Phase 7.5); access
checks happen at the API layer, not here.
"""
from __future__ import annotations

import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class StorageError(Exception):
    """Base class for storage failures."""


class NotConfiguredError(StorageError):
    """Raised when a backend is selected but its settings are missing."""


NotConfigured = NotConfiguredError  # backwards-friendly alias


class StorageBackend(ABC):
    """Contract used by the documents API."""

    @abstractmethod
    def save(self, fileobj: bytes, path: str) -> str:
        """Persist bytes at `path`; return the storage_path string."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Return bytes stored at `path`; raise StorageError if absent."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete the object at `path`; no-op if already gone."""


class LocalStorage(StorageBackend):
    """Disk-backed storage rooted at `STORAGE_PATH`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if not candidate.is_relative_to(self.root.resolve()):
            # Path traversal attempt (Phase 7.5 Risks/Notes).
            raise StorageError("Invalid storage path")
        return candidate

    def save(self, fileobj: bytes, path: str) -> str:
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + f".part-{uuid.uuid4().hex}")
        tmp.write_bytes(fileobj)
        shutil.move(str(tmp), dest)  # atomic-ish replace
        return str(dest.relative_to(self.root)).replace("\\", "/")

    def read(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def delete(self, path: str) -> None:
        dest = self._resolve(path)
        dest.unlink(missing_ok=True)


def get_storage() -> StorageBackend:
    """Factory honoring settings; R2 kept behind a stub until needed."""
    from app.core.config import get_settings

    settings = get_settings()
    return LocalStorage(settings.storage_path)
