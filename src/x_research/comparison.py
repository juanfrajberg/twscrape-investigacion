from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _read_external_direct(path: Path) -> dict[str, datetime | None]:
    records: dict[str, datetime | None] = {}
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict):
                continue
            tweet_id = str(item.get("tweet_id") or "").strip()
            if tweet_id:
                records.setdefault(tweet_id, _timestamp(item.get("date")))
    return records


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def compare_external_search(
    external_tweets_path: str | Path,
    database_path: str | Path,
    output_dir: str | Path,
    *,
    experiment_id: str,
    target_date: str = "2026-07-19",
    timezone_name: str = "America/Argentina/Buenos_Aires",
) -> dict[str, Any]:
    external_path = Path(external_tweets_path)
    database = Path(database_path)
    destination = Path(output_dir)
    if not external_path.exists():
        raise FileNotFoundError(f"No existe {external_path}")
    if not database.exists():
        raise FileNotFoundError(f"No existe {database}")

    timezone = ZoneInfo(timezone_name)
    target = date.fromisoformat(target_date)
    local_start = datetime.combine(target, time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    start_utc = local_start.astimezone(UTC)
    end_utc = local_end.astimezone(UTC)

    external_all = _read_external_direct(external_path)
    external_day = {
        tweet_id
        for tweet_id, created_at in external_all.items()
        if created_at is not None and start_utc <= created_at < end_utc
    }

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        captures = connection.execute(
            """
            SELECT DISTINCT t.tweet_id, t.created_at, j.query_family
            FROM captures c
            JOIN tweets t ON t.tweet_id = c.tweet_id
            JOIN jobs j ON j.job_id = c.job_id
            WHERE c.capture_kind = 'search' AND j.experiment_id = ?
            """,
            (experiment_id,),
        ).fetchall()
        jobs = connection.execute(
            """
            SELECT query_family, status, saturated, search_count
            FROM jobs
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        ).fetchall()
    finally:
        connection.close()

    local_dates: dict[str, datetime | None] = {}
    local_families: dict[str, set[str]] = defaultdict(set)
    for row in captures:
        tweet_id = str(row["tweet_id"])
        local_dates.setdefault(tweet_id, _timestamp(row["created_at"]))
        local_families[tweet_id].add(str(row["query_family"]))
    local_day = {
        tweet_id
        for tweet_id, created_at in local_dates.items()
        if created_at is not None and start_utc <= created_at < end_utc
    }
    overlap = external_day & local_day
    union = external_day | local_day

    hourly_rows: list[dict[str, Any]] = []
    for hour_index in range(24):
        hour_start = local_start + timedelta(hours=hour_index)
        hour_end = hour_start + timedelta(hours=1)
        external_hour = {
            tweet_id
            for tweet_id in external_day
            if external_all[tweet_id] is not None
            and hour_start <= external_all[tweet_id].astimezone(timezone) < hour_end
        }
        local_hour = {
            tweet_id
            for tweet_id in local_day
            if local_dates[tweet_id] is not None
            and hour_start <= local_dates[tweet_id].astimezone(timezone) < hour_end
        }
        hourly_rows.append(
            {
                "hour_art": hour_start.strftime("%Y-%m-%d %H:00"),
                "external_direct_unique": len(external_hour),
                "local_direct_unique": len(local_hour),
                "overlap_unique": len(external_hour & local_hour),
            }
        )

    job_metrics: dict[str, Counter[str]] = defaultdict(Counter)
    for row in jobs:
        family = str(row["query_family"])
        job_metrics[family]["jobs"] += 1
        job_metrics[family][str(row["status"])] += 1
        job_metrics[family]["saturated"] += int(row["saturated"] or 0)
        job_metrics[family]["search_count"] += int(row["search_count"] or 0)
    query_rows = []
    for family in sorted(job_metrics):
        ids = {tweet_id for tweet_id, families in local_families.items() if family in families}
        metrics = job_metrics[family]
        query_rows.append(
            {
                "query_family": family,
                "unique_tweets": len(ids),
                "jobs": metrics["jobs"],
                "completed_jobs": metrics["completed"],
                "failed_jobs": metrics["failed"],
                "saturated_jobs": metrics["saturated"],
                "search_captures": metrics["search_count"],
            }
        )

    summary = {
        "experiment_id": experiment_id,
        "target_date": target_date,
        "timezone": timezone_name,
        "external_direct_all_dates": len(external_all),
        "external_direct_target_day": len(external_day),
        "local_direct_target_day": len(local_day),
        "overlap_target_day": len(overlap),
        "external_target_recovered_fraction": (
            len(overlap) / len(external_day) if external_day else None
        ),
        "local_shared_fraction": len(overlap) / len(local_day) if local_day else None,
        "jaccard_target_day": len(overlap) / len(union) if union else None,
        "jobs": len(jobs),
        "completed_jobs": sum(row["status"] == "completed" for row in jobs),
        "failed_jobs": sum(row["status"] == "failed" for row in jobs),
        "saturated_jobs": sum(int(row["saturated"] or 0) for row in jobs),
        "comparability_note": (
            "El archivo externo no conserva consulta ni ventana de origen; la comparación exacta "
            "se limita a fecha, hora e IDs compartidos."
        ),
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "comparison_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(
        destination / "hourly_comparison.csv",
        hourly_rows,
        ("hour_art", "external_direct_unique", "local_direct_unique", "overlap_unique"),
    )
    _write_csv(
        destination / "query_comparison.csv",
        query_rows,
        (
            "query_family",
            "unique_tweets",
            "jobs",
            "completed_jobs",
            "failed_jobs",
            "saturated_jobs",
            "search_captures",
        ),
    )
    _write_csv(
        destination / "overlap_ids.csv",
        [{"tweet_id": tweet_id} for tweet_id in sorted(overlap)],
        ("tweet_id",),
    )
    return summary
