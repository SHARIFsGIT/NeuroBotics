"""Crash-consistent daily CSV/JSON archives for mission evidence.

Author: E-AIRA maintainers.
Hardware target: ROSMASTER M3 Pro / Jetson Orin NX, ROS 2 Humble / Python 3.10.
"""

import csv
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from eira_evaluation.records import CSV_FIELDS, SCHEMA_VERSION, csv_record


class DailyArchive:
    """Persist JSON first, with CSV as a recoverable projection of the JSON source."""

    def __init__(self, directory: Path, prefix: str = 'mission_log') -> None:
        """Acquire an exclusive writer lock for one output prefix.

        Args:
            directory: Results directory, created when needed.
            prefix: Safe filename prefix for daily archives.
        Raises:
            ValueError: If the prefix contains path separators.
            RuntimeError: If another writer owns the same archive prefix.
            OSError: If the output directory cannot be opened.
        """
        if not prefix or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                             '0123456789_-' for char in prefix):
            raise ValueError('archive prefix must contain only letters, digits, hyphen/underscore')
        self.directory = directory.expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self._lock = (self.directory / f'.{prefix}.lock').open('a', encoding='utf-8')
        try:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._lock.close()
            raise RuntimeError(f'another {prefix} writer is active') from exc
        self._digests: dict[str, str] = {}
        self.unmatched_commands: list[dict[str, Any]] = []
        self._known_days: set[str] = set()

    def load(self) -> list[dict[str, Any]]:
        """Load complete authoritative JSON snapshots and repair CSV projections.

        Returns:
            Existing mission records across daily files.
        Raises:
            OSError: If an existing archive is unreadable.
            ValueError: If an archive is malformed or uses an unsupported schema.
        """
        records = []
        for path in sorted(self.directory.glob(f'{self.prefix}_*.json')):
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('schema_version') != SCHEMA_VERSION or (
                    not isinstance(data.get('missions'), list)):
                raise ValueError(f'unsupported mission archive: {path}')
            if not all(isinstance(record, dict) and record.get('mission_id')
                       and isinstance(record.get('start_time'), (int, float))
                       for record in data['missions']):
                raise ValueError(f'invalid mission records in {path}')
            self._known_days.add(path.stem.rsplit('_', 1)[-1])
            records.extend(data['missions'])
            self.unmatched_commands.extend(data.get('unmatched_commands', []))
        if records or self.unmatched_commands:
            self.save(records, self.unmatched_commands)
        return records

    def _replace(self, path: Path, write: Any) -> None:
        """Atomically replace a file after flushing its complete contents.

        Args:
            path: Destination filename.
            write: Callable receiving the temporary text handle.
        Raises:
            OSError: If writing, flushing or replacing fails.
        """
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='',
                                             dir=self.directory, delete=False) as handle:
                temporary = handle.name
                write(handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
            descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def save(self, records: list[dict[str, Any]],
             unmatched_commands: list[dict[str, Any]] | None = None) -> list[Path]:
        """Commit all daily records with stable headers and strict JSON.

        Args:
            records: Detailed mission records.
            unmatched_commands: Commands whose Brain identity has not yet been observed.
        Returns:
            Paths of CSV files written during this call.
        Raises:
            OSError: If a write cannot be committed.
            ValueError: If records contain nonfinite/unserializable content.
        """
        days: dict[str, list[dict[str, Any]]] = {day: [] for day in self._known_days}
        for record in records:
            day = datetime.fromtimestamp(record['start_time'], timezone.utc).strftime('%Y%m%d')
            days.setdefault(day, []).append(record)
        commands_by_day: dict[str, list[dict[str, Any]]] = {}
        for command in unmatched_commands or []:
            day = datetime.fromtimestamp(command['received_at'], timezone.utc).strftime('%Y%m%d')
            commands_by_day.setdefault(day, []).append(command)
            days.setdefault(day, [])
        paths = []
        for day, missions in sorted(days.items()):
            encoded = json.dumps({'schema_version': SCHEMA_VERSION, 'timezone': 'UTC',
                                  'missions': missions,
                                  'unmatched_commands': commands_by_day.get(day, [])},
                                 sort_keys=True, allow_nan=False, indent=2)
            if self._digests.get(day) == encoded:
                continue
            stem = self.directory / f'{self.prefix}_{day}'
            self._replace(stem.with_suffix('.json'), lambda handle: handle.write(encoded + '\n'))

            def write_csv(handle: Any) -> None:
                """Write the explicit CSV schema for the current day's missions."""
                writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(csv_record(record) for record in missions)
            self._replace(stem.with_suffix('.csv'), write_csv)
            self._known_days.add(day)
            self._digests[day] = encoded
            paths.append(stem.with_suffix('.csv'))
        return paths

    def close(self) -> None:
        """Release the writer lock without changing any mission outcome."""
        if not self._lock.closed:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()
