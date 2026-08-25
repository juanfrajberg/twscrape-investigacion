from __future__ import annotations

import asyncio
import os
import socket
from contextlib import aclosing
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .config import ExperimentConfig, QuerySpec
from .normalize import normalize_tweet
from .storage import ResearchStore, write_jsonl_records


def twscrape_version() -> str:
    try:
        return version("twscrape")
    except PackageNotFoundError:
        return "not-installed"


def create_api(accounts_db: str | Path) -> Any:
    os.environ.setdefault("TWS_TELEMETRY", "0")
    os.environ.setdefault("TWS_HTTP_BACKEND", "curl")
    try:
        from twscrape import API
    except ImportError as error:
        raise RuntimeError(
            "twscrape no está instalado. Ejecutá: pip install '.[dev]'"
        ) from error

    return API(
        str(accounts_db),
        raise_when_no_account=True,
        wait_timeout=60,
        wait_interval=2,
    )


async def ensure_active_account(api: Any) -> None:
    pool = getattr(api, "pool", None)
    if pool is None or not hasattr(pool, "accounts_info"):
        return

    accounts = await pool.accounts_info()
    active = [account for account in accounts if bool(account["active"])]
    if not active:
        raise RuntimeError(
            "No hay cuentas activas en la base de twscrape. "
            "Agregá cookies con el comando indicado en el README."
        )


async def _collect_search(
    api: Any,
    store: ResearchStore,
    job_id: str,
    experiment: ExperimentConfig,
    query: QuerySpec,
    raw_jsonl: Path,
) -> tuple[list[Any], int, int, int]:
    seeds: list[Any] = []
    seed_ids: set[str] = set()
    fetched = 0
    duplicates = 0
    filtered_outside_window = 0
    start_epoch, end_epoch = query.epoch_bounds(experiment.timezone)
    full_query = query.full_query_for(experiment.timezone)
    stream = api.search(
        full_query,
        limit=max(query.limit * 5, 100),
        kv={"product": experiment.search_product},
    )

    async with aclosing(stream) as results:
        async for tweet in results:
            if fetched >= query.limit:
                break
            normalized = normalize_tweet(tweet)
            if not _is_in_window(normalized.created_at, start_epoch, end_epoch):
                filtered_outside_window += 1
                continue
            fetched += 1
            if normalized.tweet_id not in seed_ids:
                seeds.append(tweet)
                seed_ids.add(normalized.tweet_id)
            added = store.record_tweet(job_id, normalized, capture_kind="search")
            if added:
                write_jsonl_records(
                    raw_jsonl,
                    [
                        {
                            "job_id": job_id,
                            "experiment_id": experiment.experiment_id,
                            "query_label": query.label,
                            "full_query": full_query,
                            "capture_kind": "search",
                            "root_tweet_id": None,
                            "tweet": normalized.to_dict(),
                        }
                    ],
                )
            else:
                duplicates += 1

    return seeds, fetched, duplicates, filtered_outside_window


def _is_in_window(created_at: str | None, start_epoch: int, end_epoch: int) -> bool:
    if not created_at:
        return False
    timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return start_epoch <= timestamp.timestamp() < end_epoch


async def _collect_replies(
    api: Any,
    store: ResearchStore,
    job_id: str,
    experiment: ExperimentConfig,
    query: QuerySpec,
    raw_jsonl: Path,
    seeds: list[Any],
) -> tuple[int, int, int]:
    if (
        not experiment.download_replies
        or experiment.reply_source_limit == 0
        or experiment.replies_per_tweet == 0
    ):
        return 0, 0, 0

    candidates = sorted(
        seeds,
        key=lambda tweet: getattr(tweet, "replyCount", 0) or 0,
        reverse=True,
    )[: experiment.reply_source_limit]

    fetched = 0
    duplicates = 0
    warnings = 0

    for index, root in enumerate(candidates):
        root_id = str(getattr(root, "id_str", getattr(root, "id", "")))
        if not root_id:
            continue
        try:
            stream = api.tweet_replies(int(root_id), limit=experiment.replies_per_tweet)
            root_fetched = 0
            async with aclosing(stream) as replies:
                async for reply in replies:
                    if root_fetched >= experiment.replies_per_tweet:
                        break
                    root_fetched += 1
                    fetched += 1
                    normalized = normalize_tweet(reply)
                    added = store.record_tweet(
                        job_id,
                        normalized,
                        capture_kind="reply",
                        root_tweet_id=root_id,
                    )
                    if added:
                        write_jsonl_records(
                            raw_jsonl,
                            [
                                {
                                    "job_id": job_id,
                                    "experiment_id": experiment.experiment_id,
                                    "query_label": query.label,
                                    "full_query": query.full_query_for(experiment.timezone),
                                    "capture_kind": "reply",
                                    "root_tweet_id": root_id,
                                    "tweet": normalized.to_dict(),
                                }
                            ],
                        )
                    else:
                        duplicates += 1
        except Exception as error:  # la librería expone excepciones variables según X
            warnings += 1
            store.add_event(
                job_id,
                "warning",
                f"No se pudieron descargar respuestas de {root_id}: {error}",
            )

        if index < len(candidates) - 1 and experiment.reply_delay_seconds:
            await asyncio.sleep(experiment.reply_delay_seconds)

    return fetched, duplicates, warnings


async def collect_experiment(
    experiment: ExperimentConfig,
    *,
    accounts_db: str | Path,
    database_path: str | Path,
    raw_jsonl: str | Path,
    force: bool = False,
    api: Any | None = None,
) -> list[dict[str, Any]]:
    store = ResearchStore(database_path)
    raw_path = Path(raw_jsonl)
    client = api or create_api(accounts_db)
    if api is None:
        await ensure_active_account(client)

    reports: list[dict[str, Any]] = []
    for query in experiment.queries:
        job_id, should_run = store.prepare_job(
            experiment,
            query,
            machine=socket.gethostname(),
            twscrape_version=twscrape_version(),
            force=force,
        )
        if not should_run:
            reports.append(
                {
                    "job_id": job_id,
                    "query_label": query.label,
                    "status": "skipped-completed",
                }
            )
            continue

        fetched = 0
        duplicates = 0
        warnings = 0
        try:
            (
                seeds,
                search_fetched,
                search_duplicates,
                filtered_outside_window,
            ) = await _collect_search(
                client, store, job_id, experiment, query, raw_path
            )
            if search_fetched < query.minimum_results:
                raise RuntimeError(
                    "La búsqueda devolvió "
                    f"{search_fetched} resultados y se esperaban al menos "
                    f"{query.minimum_results}. Revisá los eventos de twscrape, la cuenta "
                    "y la consulta."
                )
            fetched += search_fetched
            duplicates += search_duplicates
            if filtered_outside_window:
                store.add_event(
                    job_id,
                    "info",
                    f"Se descartaron {filtered_outside_window} resultados fuera del período",
                )

            reply_fetched, reply_duplicates, reply_warnings = await _collect_replies(
                client,
                store,
                job_id,
                experiment,
                query,
                raw_path,
                seeds,
            )
            fetched += reply_fetched
            duplicates += reply_duplicates
            warnings += reply_warnings

            store.finish_job(
                job_id,
                status="completed",
                fetched_count=fetched,
                duplicate_count=duplicates,
                warning_count=warnings,
            )
            reports.append(
                {
                    "job_id": job_id,
                    "query_label": query.label,
                    "status": "completed",
                    "fetched": fetched,
                    "duplicates": duplicates,
                    "warnings": warnings,
                    "filtered_outside_window": filtered_outside_window,
                }
            )
        except Exception as error:
            store.add_event(job_id, "error", str(error))
            store.finish_job(
                job_id,
                status="failed",
                fetched_count=fetched,
                duplicate_count=duplicates,
                warning_count=warnings,
                error_message=str(error),
            )
            raise RuntimeError(
                f"Falló la consulta '{query.label}'. El progreso guardado no se pierde: {error}"
            ) from error

    return reports
