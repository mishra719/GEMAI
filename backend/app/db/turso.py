"""
Pure-Python DBAPI 2.0 adapter for Turso (libSQL) via the HTTP Pipeline API.

This module lets SQLAlchemy talk to a remote Turso database without any
native / compiled dependencies — only `httpx` is required.

Register the dialect so that SQLAlchemy URLs of the form
``sqlite+turso://…`` are handled automatically.
"""

from __future__ import annotations

import itertools
import logging
import re
from typing import Any, Optional, Sequence

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DBAPI 2.0 globals
# ---------------------------------------------------------------------------
apilevel = "2.0"
threadsafety = 1
paramstyle = "qmark"


# ---------------------------------------------------------------------------
# DBAPI 2.0 exceptions
# ---------------------------------------------------------------------------
class Error(Exception):
    pass


class DatabaseError(Error):
    pass


class OperationalError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NAMED_PARAM = re.compile(r":([a-zA-Z_]\w*)")


def _convert_params(sql: str, params: Any | None):
    """
    Convert SQLAlchemy's named-parameter style (``:name``) to Turso's
    positional ``?`` style and return the rewritten SQL plus a flat list
    of argument values.
    """
    if params is None:
        return sql, []

    if isinstance(params, dict):
        ordered_args: list[Any] = []
        def _replace(m):
            ordered_args.append(params[m.group(1)])
            return "?"
        sql = _NAMED_PARAM.sub(_replace, sql)
        return sql, ordered_args

    # Already a sequence of positional args
    return sql, list(params)


def _turso_value(val: Any) -> dict:
    """Encode a Python value into a Turso ``Value`` object."""
    if val is None:
        return {"type": "null", "value": None}
    if isinstance(val, bool):
        return {"type": "integer", "value": str(int(val))}
    if isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    if isinstance(val, float):
        return {"type": "float", "value": val}
    if isinstance(val, bytes):
        import base64
        return {"type": "blob", "base64": base64.b64encode(val).decode()}
    return {"type": "text", "value": str(val)}


def _python_value(col: dict) -> Any:
    """Decode a Turso ``Value`` object back to a Python value."""
    t = col.get("type", "text")
    v = col.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    if t == "blob":
        import base64
        return base64.b64decode(col.get("base64", v))
    return str(v)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

class Connection:
    """DBAPI 2.0 ``Connection`` backed by the Turso HTTP pipeline API."""

    def __init__(self, http_url: str, auth_token: str):
        self._url = http_url.rstrip("/") + "/v2/pipeline"
        self._token = auth_token
        self._client = httpx.Client(timeout=30.0)
        self._closed = False

    # -- pipeline helper ---------------------------------------------------

    def _pipeline(self, requests: list[dict]) -> list[dict]:
        resp = self._client.post(
            self._url,
            json={"requests": requests},
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code >= 400:
            raise OperationalError(
                f"Turso HTTP {resp.status_code}: {resp.text}"
            )
        body = resp.json()
        results = body.get("results", [])
        for r in results:
            if r.get("type") == "error":
                err = r.get("error", {})
                msg = err.get("message", str(err))
                code = err.get("code", "")
                if "UNIQUE constraint" in msg or "CONSTRAINT" in msg:
                    raise IntegrityError(msg)
                raise DatabaseError(f"[{code}] {msg}")
        return results

    def execute_sql(self, sql: str, args: list[Any] | None = None) -> dict:
        """Execute a single SQL statement and return the result object."""
        stmt: dict[str, Any] = {"sql": sql}
        if args:
            stmt["args"] = [_turso_value(a) for a in args]
        results = self._pipeline([{"type": "execute", "stmt": stmt}])
        if results:
            return results[0].get("response", {}).get("result", {})
        return {}

    # -- DBAPI interface ---------------------------------------------------

    def cursor(self) -> "Cursor":
        if self._closed:
            raise ProgrammingError("Connection is closed")
        return Cursor(self)

    def commit(self):
        pass  # auto-commit; Turso HTTP pipeline has no persistent txn

    def rollback(self):
        pass

    # -- SQLite dialect compatibility stubs --------------------------------

    def create_function(self, name, narg, func, **kw):
        """No-op: the Turso HTTP API doesn't support user-defined functions."""
        pass

    def create_collation(self, name, callable_):
        """No-op: the Turso HTTP API doesn't support custom collations."""
        pass

    def close(self):
        self._closed = True
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------

class Cursor:
    """DBAPI 2.0 ``Cursor``."""

    arraysize = 1

    def __init__(self, conn: Connection):
        self._conn = conn
        self.description: list[tuple] | None = None
        self.rowcount: int = -1
        self._rows: list[tuple] = []
        self._iter: Any = iter([])
        self.lastrowid: int | None = None

    def execute(self, sql: str, params: Any = None):
        sql, args = _convert_params(sql, params)
        result = self._conn.execute_sql(sql, args)

        cols = result.get("cols", [])
        rows_raw = result.get("rows", [])
        affected = result.get("affected_row_count", 0)
        last_id = result.get("last_insert_rowid")

        if cols:
            self.description = [
                (c.get("name", f"col{i}"), None, None, None, None, None, None)
                for i, c in enumerate(cols)
            ]
        else:
            self.description = None

        self._rows = [
            tuple(_python_value(cell) for cell in row) for row in rows_raw
        ]
        self._iter = iter(self._rows)
        self.rowcount = affected if not rows_raw else len(rows_raw)
        self.lastrowid = int(last_id) if last_id is not None else None

    def executemany(self, sql: str, seq_of_params: Sequence):
        for params in seq_of_params:
            self.execute(sql, params)

    def fetchone(self) -> tuple | None:
        try:
            return next(self._iter)
        except StopIteration:
            return None

    def fetchmany(self, size: int | None = None) -> list[tuple]:
        size = size or self.arraysize
        return list(itertools.islice(self._iter, size))

    def fetchall(self) -> list[tuple]:
        return list(self._iter)

    def close(self):
        self._rows = []
        self._iter = iter([])

    @property
    def _is_select(self) -> bool:
        return self.description is not None

    def __iter__(self):
        return self._iter


# ---------------------------------------------------------------------------
# Module-level ``connect`` (DBAPI 2.0 entry-point)
# ---------------------------------------------------------------------------

def connect(http_url: str = "", auth_token: str = "", **_kw) -> Connection:
    return Connection(http_url=http_url, auth_token=auth_token)
