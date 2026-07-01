"""
File System Navigator
=====================
Safe read-only navigation of the file system.
All operations pass through the PermissionManager.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from jarvis.desktop.permissions import PermissionManager


@dataclass
class FileInfo:
    """Metadata for a file or directory."""
    name: str
    path: str
    is_dir: bool
    size_bytes: int = 0
    modified_at: float = 0.0
    extension: str = ""
    mime_type: str = ""


class FileNavigator:
    """
    Safe file system navigator with permission enforcement.

    Usage:
        nav = FileNavigator(permissions=pm)
        entries = await nav.list_directory("~/Documents")
        info = await nav.get_file_info("~/Documents/report.pdf")
        content = await nav.read_text_file("~/Documents/notes.txt")
    """

    MAX_FILE_READ_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, permissions: PermissionManager) -> None:
        self._permissions = permissions

    async def list_directory(
        self,
        path: str,
        *,
        show_hidden: bool = False,
        sort_by: str = "name",    # name | size | modified
        limit: int = 100,
    ) -> list[FileInfo]:
        """List contents of a directory."""
        abs_path = str(Path(path).expanduser().resolve())

        if not self._permissions.check_path(abs_path):
            raise PermissionError(f"Access to {abs_path} is not permitted")

        if not os.path.isdir(abs_path):
            raise NotADirectoryError(f"Not a directory: {abs_path}")

        entries = []
        with os.scandir(abs_path) as scanner:
            for entry in scanner:
                if not show_hidden and entry.name.startswith("."):
                    continue
                try:
                    stat = entry.stat()
                    entries.append(FileInfo(
                        name=entry.name,
                        path=entry.path,
                        is_dir=entry.is_dir(),
                        size_bytes=stat.st_size if not entry.is_dir() else 0,
                        modified_at=stat.st_mtime,
                        extension=Path(entry.name).suffix.lower(),
                    ))
                except (PermissionError, OSError):
                    continue

        # Sort
        key_map = {
            "name": lambda e: e.name.lower(),
            "size": lambda e: e.size_bytes,
            "modified": lambda e: e.modified_at,
        }
        entries.sort(key=key_map.get(sort_by, key_map["name"]))
        return entries[:limit]

    async def get_file_info(self, path: str) -> FileInfo:
        """Get metadata for a single file or directory."""
        abs_path = str(Path(path).expanduser().resolve())
        if not self._permissions.check_path(abs_path):
            raise PermissionError(f"Access denied: {abs_path}")

        p = Path(abs_path)
        if not p.exists():
            raise FileNotFoundError(f"Not found: {abs_path}")

        stat = p.stat()
        return FileInfo(
            name=p.name,
            path=abs_path,
            is_dir=p.is_dir(),
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
            extension=p.suffix.lower(),
        )

    async def read_text_file(
        self, path: str, max_chars: int = 50_000
    ) -> str:
        """Read a text file and return its contents."""
        abs_path = str(Path(path).expanduser().resolve())
        if not self._permissions.check_path(abs_path):
            raise PermissionError(f"Access denied: {abs_path}")

        p = Path(abs_path)
        size = p.stat().st_size
        if size > self.MAX_FILE_READ_SIZE:
            raise ValueError(
                f"File too large to read: {size / 1024 / 1024:.1f} MB "
                f"(max: {self.MAX_FILE_READ_SIZE / 1024 / 1024:.0f} MB)"
            )

        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[Truncated at {max_chars} chars]"
        return text

    async def search_files(
        self,
        directory: str,
        pattern: str,
        *,
        recursive: bool = True,
        max_results: int = 50,
    ) -> list[FileInfo]:
        """Search for files matching a glob pattern."""
        abs_dir = str(Path(directory).expanduser().resolve())
        if not self._permissions.check_path(abs_dir):
            raise PermissionError(f"Access denied: {abs_dir}")

        results = []
        base = Path(abs_dir)
        glob_func = base.rglob if recursive else base.glob

        for p in glob_func(pattern):
            if len(results) >= max_results:
                break
            if not self._permissions.check_path(str(p)):
                continue
            try:
                stat = p.stat()
                results.append(FileInfo(
                    name=p.name,
                    path=str(p),
                    is_dir=p.is_dir(),
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                    extension=p.suffix.lower(),
                ))
            except OSError:
                continue

        return results
