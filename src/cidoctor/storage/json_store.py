"""JSON run-history store for CI Doctor.

One file per run, named ``<UTC timestamp>_<short id>.json``, containing a
``schema_version`` and the :class:`~cidoctor.core.models.Run` model dump.

Security rules:
* Run ids may contain only letters, digits, underscore and hyphen.
* Resolved paths must stay inside the store directory (no traversal).
* Symlinks that escape the store directory are skipped.
* A 50 MB file size limit is enforced.
* Corrupt files and unknown schema versions are skipped with a logged warning
  and never crash a command. IO errors are wrapped in :class:`StorageError`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cidoctor.core.errors import StorageError
from cidoctor.core.models import Run

logger = logging.getLogger(__name__)

DEFAULT_STORE_PATH = Path(".cidoctor/runs")
DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
SCHEMA_VERSION = 1

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_FILENAME_TS_RE = re.compile(r"^(\d{8}T\d{6}\d{6})_")


def _utc_now_filename() -> str:
    """Return a sortable UTC timestamp for filenames (YYYYmmddTHHMMSSffffff)."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")


def _parse_filename_timestamp(name: str) -> str | None:
    """Extract the sortable timestamp prefix from a run filename."""
    match = _FILENAME_TS_RE.match(name)
    return match.group(1) if match else None


class JsonStore:
    """Concrete JSON file-based store implementing :class:`Store`."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_STORE_PATH
        self.path.mkdir(parents=True, exist_ok=True)
        # Per-instance cache for repeated test_history calls within one command.
        self._cache: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
        # Cache of parsed Run objects keyed by file path, so repeated
        # test_history calls for different tests don't re-read the same file.
        self._run_cache: dict[Path, Run | None] = {}
        # Lazy-built index of test_name -> history entries (since=None only).
        self._test_index: dict[str, list[dict[str, Any]]] | None = None

    # -- internal helpers -------------------------------------------------

    def _validate_run_id(self, run_id: str) -> None:
        if not _RUN_ID_RE.match(run_id):
            raise StorageError(
                f"invalid run id {run_id!r}: only letters, digits, "
                "underscore and hyphen are allowed"
            )

    def _resolve_within_store(self, file_name: str) -> Path:
        """Resolve ``file_name`` inside the store dir, rejecting traversal."""
        candidate = (self.path / file_name).resolve()
        store_resolved = self.path.resolve()
        try:
            candidate.relative_to(store_resolved)
        except ValueError as exc:
            raise StorageError(
                f"path escapes store directory: {file_name}"
            ) from exc
        return candidate

    def _list_run_files(self) -> list[Path]:
        """Return run files sorted by filename timestamp descending.

        Symlinks are skipped. Non-.json files are ignored.
        """
        files: list[Path] = []
        for entry in self.path.iterdir():
            if not entry.is_file() or entry.is_symlink():
                continue
            if entry.suffix != ".json":
                continue
            files.append(entry)
        files.sort(
            key=lambda p: _parse_filename_timestamp(p.name) or "", reverse=True
        )
        return files

    def _read_run_file(self, path: Path) -> Run | None:
        """Parse a single run file, returning None on corrupt/unknown schema."""
        # Check cache first.
        if path in self._run_cache:
            return self._run_cache[path]

        try:
            size = path.stat().st_size
        except OSError as exc:
            logger.warning("cannot stat %s: %s", path, exc)
            self._run_cache[path] = None
            return None
        if size > DEFAULT_MAX_FILE_SIZE:
            logger.warning("file %s exceeds size limit, skipping", path)
            self._run_cache[path] = None
            return None

        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("skipping corrupt run file %s: %s", path, exc)
            self._run_cache[path] = None
            return None

        if not isinstance(data, dict):
            logger.warning("skipping non-object run file %s", path)
            self._run_cache[path] = None
            return None
        if data.get("schema_version") != SCHEMA_VERSION:
            logger.warning(
                "skipping unknown schema version %s in %s",
                data.get("schema_version"),
                path,
            )
            self._run_cache[path] = None
            return None

        run_data = data.get("run")
        if not isinstance(run_data, dict):
            logger.warning("skipping run file %s without a 'run' object", path)
            self._run_cache[path] = None
            return None

        try:
            run = Run.model_validate(run_data)
        except Exception as exc:  # noqa: BLE001 - corrupt file is skipped
            logger.warning("skipping invalid run data in %s: %s", path, exc)
            self._run_cache[path] = None
            return None

        self._run_cache[path] = run
        return run

    # -- Store protocol ---------------------------------------------------

    def save_run(self, run: Run) -> None:
        """Persist ``run`` atomically via temp file + ``os.replace``."""
        self._validate_run_id(run.id)
        timestamp = _utc_now_filename()
        short_id = f"{run.id[:8]}_{uuid.uuid4().hex[:6]}"
        file_name = f"{timestamp}_{short_id}.json"
        target = self._resolve_within_store(file_name)

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run": run.model_dump(),
        }

        # Write to a temp file in the same directory, then atomically replace.
        tmp_name: str | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(
                dir=str(self.path), prefix=".tmp_", suffix=".json"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, default=str)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, target)
            tmp_name = None
            self._test_index = None  # new run invalidates the test index
        except Exception:  # noqa: BLE001 - wrap all save failures in StorageError
            raise StorageError(f"failed to save run {run.id}") from None
        finally:
            if tmp_name is not None:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass

    def get_run(self, id_or_latest: str) -> Run | None:
        if id_or_latest == "latest":
            latest_run: Run | None = None
            for path in self._list_run_files():
                run = self._read_run_file(path)
                if run is None:
                    continue
                if latest_run is None or run.created_at > latest_run.created_at:
                    latest_run = run
            return latest_run

        # Specific id: scan files sorted newest first, parse until match.
        for path in self._list_run_files():
            run = self._read_run_file(path)
            if run is not None and run.id == id_or_latest:
                return run
        return None

    def list_runs(
        self, since: datetime | None = None, branch: str | None = None
    ) -> list[Run]:
        since_ts = since.strftime("%Y%m%dT%H%M%S") if since else None
        runs: list[Run] = []
        for path in self._list_run_files():
            if since_ts is not None:
                ts = _parse_filename_timestamp(path.name)
                if ts is not None and ts < since_ts:
                    # Filename timestamps are sorted desc; stop early.
                    break
            run = self._read_run_file(path)
            if run is None:
                continue
            if since is not None and run.created_at < since:
                continue
            if branch is not None and run.branch != branch:
                continue
            runs.append(run)
        return runs

    def test_history(
        self, name: str, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        cache_key = (name, since.isoformat() if since else None)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # When since is None, use a pre-built index for O(1) lookups.
        if since is None:
            if self._test_index is None:
                self._test_index = self._build_test_index()
            indexed: list[dict[str, Any]] = self._test_index.get(name, [])
            self._cache[cache_key] = indexed
            return indexed

        since_ts = since.strftime("%Y%m%dT%H%M%S")
        history: list[dict[str, Any]] = []
        for path in self._list_run_files():
            ts = _parse_filename_timestamp(path.name)
            if ts is not None and ts < since_ts:
                break
            run = self._read_run_file(path)
            if run is None:
                continue
            if run.created_at < since:
                continue
            for result in run.results:
                if result.name != name:
                    continue
                history.append(
                    {
                        "run_id": run.id,
                        "commit": run.commit,
                        "branch": run.branch,
                        "created_at": run.created_at.isoformat(),
                        "status": result.status,
                    }
                )
        self._cache[cache_key] = history
        return history

    def _build_test_index(self) -> dict[str, list[dict[str, Any]]]:
        """Build an index of test_name -> history entries (since=None).

        Iterates through all runs once, grouping results by test name.
        """
        index: dict[str, list[dict[str, Any]]] = {}
        for path in self._list_run_files():
            run = self._read_run_file(path)
            if run is None:
                continue
            for result in run.results:
                entry = {
                    "run_id": run.id,
                    "commit": run.commit,
                    "branch": run.branch,
                    "created_at": run.created_at.isoformat(),
                    "status": result.status,
                }
                index.setdefault(result.name, []).append(entry)
        return index

    def past_failures_for_fingerprint(
        self, fingerprint: str, limit: int = 10
    ) -> list[str]:
        from cidoctor.core.fingerprint import fingerprint as compute_fp

        found: list[str] = []
        seen: set[str] = set()
        for path in self._list_run_files():
            run = self._read_run_file(path)
            if run is None:
                continue
            for result in run.results:
                if result.status in {"passed", "skipped"}:
                    continue
                fp = compute_fp(result.message, result.trace)
                if fp == fingerprint and result.name not in seen:
                    seen.add(result.name)
                    found.append(result.name)
                    if len(found) >= limit:
                        return found
        return found
