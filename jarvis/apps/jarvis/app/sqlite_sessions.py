"""Reuse idle SQLite handles, never transactions or query results.

Only the live Jarvis runtime owns these pools. Every checkout has its own handle,
including nested checkouts. Existing commit/rollback boundaries and SQLite's
FULL synchronous default are preserved. Closing a pool never closes an active
borrower's handle; that handle closes on return. No waiting for a pooled slot.
"""
from contextlib import contextmanager
import sqlite3
import threading


class _Cursor:
    def __init__(self, lease, cursor):
        self._lease, self._cursor = lease, cursor

    def __getattr__(self, name):
        self._lease._check()
        if name == 'connection':
            return self._lease
        value = getattr(self._cursor, name)
        if not callable(value):
            return value
        def call(*args, **kwargs):
            self._lease._check()
            result = value(*args, **kwargs)
            return self if result is self._cursor else result
        return call

    def __iter__(self):
        self._lease._check()
        return self

    def __next__(self):
        self._lease._check()
        return next(self._cursor)


class _Lease:
    """An expired checkout cannot be used, even if the raw handle is cached."""
    def __init__(self, connection):
        self._connection = connection
        self._active = True
        self._thread_id = threading.get_ident()
        self._cursors = []

    def _check(self):
        if not self._active:
            raise sqlite3.ProgrammingError('SQLite checkout is closed.')
        if threading.get_ident() != self._thread_id:
            raise sqlite3.ProgrammingError('SQLite checkout belongs to another thread.')

    def __enter__(self):
        self._check()
        self._connection.__enter__()
        return self

    def __exit__(self, *args):
        self._check()
        return self._connection.__exit__(*args)

    def __getattr__(self, name):
        self._check()
        value = getattr(self._connection, name)
        if not callable(value):
            return value
        def call(*args, **kwargs):
            self._check()
            if name == 'backup' and args and isinstance(args[0], _Lease):
                args[0]._check()
                args = (args[0]._connection, *args[1:])
            result = value(*args, **kwargs)
            if isinstance(result, sqlite3.Cursor):
                self._cursors.append(result)
                return _Cursor(self, result)
            return result
        return call

    def _expire(self):
        self._active = False
        for cursor in self._cursors:
            try:
                cursor.close()
            except sqlite3.ProgrammingError:
                pass
        self._cursors.clear()


class SQLiteSessions:
    def __init__(self, path, *, rows=False, foreign_keys=False, max_idle=2):
        self.path, self.rows, self.foreign_keys = path, rows, foreign_keys
        self.max_idle = max_idle
        self._idle = []
        self._lock = threading.Lock()
        self._closed = False

    def _take(self):
        with self._lock:
            if self._closed:
                raise sqlite3.ProgrammingError('SQLite session pool is closed.')
            if self._idle:
                return self._idle.pop()
        # Each handle is used exclusively by one borrower, not concurrently.
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        try:
            if self.rows:
                connection.row_factory = sqlite3.Row
            if self.foreign_keys:
                connection.execute('PRAGMA foreign_keys=ON')
            return connection
        except BaseException:
            connection.close()
            raise

    @contextmanager
    def connect(self):
        connection = self._take()
        lease = _Lease(connection)
        reusable = False
        try:
            with connection:
                yield lease
            reusable = not connection.in_transaction
        finally:
            lease._expire()
            with self._lock:
                if reusable and not self._closed and len(self._idle) < self.max_idle:
                    self._idle.append(connection)
                else:
                    connection.close()

    def close(self):
        with self._lock:
            self._closed = True
            idle, self._idle = self._idle, []
        for connection in idle:
            connection.close()
