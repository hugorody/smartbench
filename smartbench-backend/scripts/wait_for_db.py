"""Wait until PostgreSQL is reachable."""

from __future__ import annotations

import os
import time

import psycopg


def main() -> None:
    dsn = os.getenv(
        "DATABASE_URL",
        "postgresql://smartbench:smartbench@postgres:5432/smartbench",
    )
    # SQLAlchemy URL may include +psycopg, which psycopg does not accept.
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    timeout_seconds = 60
    start = time.time()

    while True:
        try:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            print("database is ready")
            return
        except Exception as exc:  # pragma: no cover - operational utility
            if time.time() - start > timeout_seconds:
                raise RuntimeError("database readiness timeout") from exc
            print("waiting for database...", exc)
            time.sleep(2)


if __name__ == "__main__":
    main()
