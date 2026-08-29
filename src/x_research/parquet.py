from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _pyarrow_modules() -> tuple[Any, Any]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "La exportación Parquet requiere la dependencia opcional: "
            "python -m pip install '.[mass]'"
        ) from error
    return pa, pq


def _safe_partition(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned or "sin_valor"


def _arrow_type(pa: Any, sqlite_type: str) -> Any:
    normalized = sqlite_type.upper()
    if "INT" in normalized:
        return pa.int64()
    if any(name in normalized for name in ("REAL", "FLOA", "DOUB")):
        return pa.float64()
    return pa.string()


def _query_schema(
    pa: Any,
    cursor: sqlite3.Cursor,
    declared_types: dict[str, str],
) -> Any:
    fields = []
    for description in cursor.description or ():
        name = description[0]
        fields.append(pa.field(name, _arrow_type(pa, declared_types.get(name, "TEXT"))))
    return pa.schema(fields)


def _table_types(database: sqlite3.Connection, table: str) -> dict[str, str]:
    return {
        row["name"]: row["type"]
        for row in database.execute(f"PRAGMA table_info('{table}')").fetchall()
    }


def _write_query(
    database: sqlite3.Connection,
    sql: str,
    parameters: Iterable[Any],
    destination: Path,
    *,
    declared_types: dict[str, str],
    batch_size: int = 50_000,
) -> int:
    pa, pq = _pyarrow_modules()
    cursor = database.execute(sql, tuple(parameters))
    schema = _query_schema(pa, cursor, declared_types)
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    writer = None
    try:
        while rows := cursor.fetchmany(batch_size):
            records = [dict(row) for row in rows]
            table = pa.Table.from_pylist(records, schema=schema)
            if writer is None:
                writer = pq.ParquetWriter(
                    destination,
                    schema,
                    compression="zstd",
                    use_dictionary=True,
                )
            writer.write_table(table)
            total += len(records)
    finally:
        if writer is not None:
            writer.close()
    return total


def export_parquet_dataset(
    database_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = Path(database_path)
    destination = Path(output_dir)
    if not source.exists():
        raise FileNotFoundError(f"No existe la base: {source}")
    if destination.exists() and not destination.is_dir():
        raise RuntimeError(f"La salida no es un directorio: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(
            f"El directorio {destination} no está vacío. Usá una carpeta nueva "
            "para evitar mezclar exportaciones."
        )
    destination.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {"database": str(source), "output": str(destination)}
    with sqlite3.connect(source) as database:
        database.row_factory = sqlite3.Row
        tweets_types = _table_types(database, "tweets")
        tweet_dates = [
            row["tweet_date"]
            for row in database.execute(
                """
                SELECT DISTINCT COALESCE(SUBSTR(created_at, 1, 10), 'sin_fecha')
                    AS tweet_date
                FROM tweets
                ORDER BY tweet_date
                """
            ).fetchall()
        ]
        tweet_total = 0
        for tweet_date in tweet_dates:
            tweet_total += _write_query(
                database,
                """
                SELECT * FROM tweets
                WHERE COALESCE(SUBSTR(created_at, 1, 10), 'sin_fecha') = ?
                ORDER BY created_at, tweet_id
                """,
                (tweet_date,),
                destination
                / "tweets"
                / f"date={_safe_partition(tweet_date)}"
                / "part-00000.parquet",
                declared_types=tweets_types,
            )
        report["tweets"] = tweet_total

        capture_types = {
            **_table_types(database, "captures"),
            **_table_types(database, "jobs"),
        }
        partitions = database.execute(
            """
            SELECT DISTINCT
                COALESCE(NULLIF(j.corpus_layer, ''), 'core') AS corpus_layer,
                COALESCE(NULLIF(j.query_family, ''), 'sin_familia') AS query_family
            FROM captures c
            JOIN jobs j ON j.job_id = c.job_id
            ORDER BY j.corpus_layer, j.query_family
            """
        ).fetchall()
        capture_total = 0
        for partition in partitions:
            layer = partition["corpus_layer"] or "core"
            family = partition["query_family"] or "sin_familia"
            capture_total += _write_query(
                database,
                """
                SELECT
                    c.id, c.job_id, c.tweet_id, c.capture_kind,
                    c.root_tweet_id, c.captured_at,
                    j.experiment_id, j.query_label, j.query_family,
                    j.corpus_layer, j.since_date, j.until_date
                FROM captures c
                JOIN jobs j ON j.job_id = c.job_id
                WHERE COALESCE(NULLIF(j.corpus_layer, ''), 'core') = ?
                  AND COALESCE(NULLIF(j.query_family, ''), 'sin_familia') = ?
                ORDER BY c.id
                """,
                (layer, family),
                destination
                / "captures"
                / f"layer={_safe_partition(layer)}"
                / f"family={_safe_partition(family)}"
                / "part-00000.parquet",
                declared_types=capture_types,
            )
        report["captures"] = capture_total

        for table in ("users", "user_snapshots", "relationships", "jobs", "job_events"):
            count = _write_query(
                database,
                f"SELECT * FROM {table}",
                (),
                destination / f"{table}.parquet",
                declared_types=_table_types(database, table),
            )
            report[table] = count

    return report
