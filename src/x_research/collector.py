from __future__ import annotations

import asyncio
import os
import re
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
        wait_timeout=1200,
        wait_interval=2,
    )


def _raw_path_for_job(
    raw_target: str | Path,
    experiment: ExperimentConfig,
    query: QuerySpec,
    job_id: str,
) -> Path:
    target = Path(raw_target)
    if target.suffix.lower() == ".jsonl":
        return target
    safe_experiment = re.sub(r"[^A-Za-z0-9_.-]+", "_", experiment.experiment_id)
    safe_family = re.sub(r"[^A-Za-z0-9_.-]+", "_", query.family)
    return target / safe_experiment / safe_family / f"{job_id}.jsonl"


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
    raw_target: Path,
) -> tuple[list[Any], int, int, int, bool]:
    seeds: list[Any] = []
    seed_ids: set[str] = set()
    fetched = 0
    duplicates = 0
    filtered_outside_window = 0
    start_epoch, end_epoch = query.epoch_bounds(experiment.timezone)
    full_query = query.full_query_for(experiment.timezone)
    raw_jsonl = _raw_path_for_job(raw_target, experiment, query, job_id)
    stream = api.search(
        full_query,
        limit=max(query.limit * 5, 100),
        kv={"product": experiment.search_product},
    )

    async with aclosing(stream) as results:
        async for tweet in results:
            if len(seed_ids) >= query.limit:
                break
            normalized = normalize_tweet(tweet)
            if not _is_in_window(normalized.created_at, start_epoch, end_epoch):
                filtered_outside_window += 1
                continue
            if normalized.tweet_id in seed_ids:
                duplicates += 1
                continue
            seeds.append(tweet)
            seed_ids.add(normalized.tweet_id)
            fetched += 1
            is_thread_root = (
                query.corpus_layer == "thread"
                and normalized.tweet_id == query.conversation_id
            )
            capture_kind = (
                "reply"
                if query.corpus_layer == "thread" and not is_thread_root
                else "search"
            )
            root_tweet_id = query.conversation_id or None
            added = store.record_tweet(
                job_id,
                normalized,
                capture_kind=capture_kind,
                root_tweet_id=root_tweet_id,
            )
            if added:
                write_jsonl_records(
                    raw_jsonl,
                    [
                        {
                            "job_id": job_id,
                            "experiment_id": experiment.experiment_id,
                            "query_label": query.label,
                            "query_family": query.family,
                            "corpus_layer": query.corpus_layer,
                            "full_query": full_query,
                            "capture_kind": capture_kind,
                            "root_tweet_id": root_tweet_id,
                            "tweet": normalized.to_dict(),
                        }
                    ],
                )
            else:
                duplicates += 1

    return seeds, fetched, duplicates, filtered_outside_window, len(seed_ids) >= query.limit


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
    raw_target: Path,
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
        raw_jsonl = _raw_path_for_job(raw_target, experiment, query, job_id)
        try:
            stream = api.tweet_replies(
                int(root_id),
                limit=max(experiment.replies_per_tweet * 5, 100),
            )
            root_fetched = 0
            root_seen: set[str] = set()
            async with aclosing(stream) as replies:
                async for reply in replies:
                    if root_fetched >= experiment.replies_per_tweet:
                        break
                    normalized = normalize_tweet(reply)
                    if (
                        normalized.tweet_id == root_id
                        or normalized.tweet_id in root_seen
                    ):
                        duplicates += 1
                        continue
                    root_seen.add(normalized.tweet_id)
                    root_fetched += 1
                    fetched += 1
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
                                    "query_family": query.family,
                                    "corpus_layer": query.corpus_layer,
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
    continue_on_error: bool = False,
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
        search_fetched = 0
        duplicates = 0
        warnings = 0
        try:
            (
                seeds,
                search_fetched,
                search_duplicates,
                filtered_outside_window,
                saturated,
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
            if saturated:
                store.add_event(
                    job_id,
                    "warning",
                    "La ventana alcanzó el límite configurado y puede estar truncada; "
                    "debe subdividirse.",
                )
                warnings += 1

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
                search_count=search_fetched,
                saturated=saturated,
            )
            reports.append(
                {
                    "job_id": job_id,
                    "query_label": query.label,
                    "status": "completed",
                    "fetched": fetched,
                    "duplicates": duplicates,
                    "warnings": warnings,
                    "saturated": saturated,
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
                search_count=search_fetched,
                error_message=str(error),
            )
            message = (
                f"Falló la consulta '{query.label}'. "
                f"El progreso guardado no se pierde: {error}"
            )
            reports.append(
                {
                    "job_id": job_id,
                    "query_label": query.label,
                    "status": "failed",
                    "error": str(error),
                }
            )
            if not continue_on_error:
                raise RuntimeError(message) from error

    return reports
