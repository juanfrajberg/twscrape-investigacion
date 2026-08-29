from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import ExperimentConfig, QuerySpec, _parse_local_boundary


@dataclass(frozen=True)
class CampaignQuery:
    label: str
    text: str
    corpus_layer: str
    window_minutes: int
    limit: int
    minimum_results: int
    minimum_window_minutes: int


@dataclass(frozen=True)
class WindowOverride:
    label: str
    since: str
    until: str
    window_minutes: int
    query_families: tuple[str, ...]

    def boundaries(self) -> tuple[datetime, datetime]:
        return _parse_local_boundary(self.since), _parse_local_boundary(self.until)

    def applies_to(self, query_family: str) -> bool:
        return not self.query_families or query_family in self.query_families


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    description: str
    timezone: str
    since: str
    until: str
    search_product: str
    default_window_minutes: int
    limit_per_job: int
    minimum_window_minutes: int
    queries: tuple[CampaignQuery, ...]
    overrides: tuple[WindowOverride, ...]

    def boundaries(self) -> tuple[datetime, datetime]:
        return _parse_local_boundary(self.since), _parse_local_boundary(self.until)


def _text(data: dict[str, Any], key: str, context: str, *, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: '{key}' debe ser un texto no vacío")
    return value.strip()


def _positive_int(
    data: dict[str, Any], key: str, context: str, *, default: int | None = None
) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{context}: '{key}' debe ser un entero positivo")
    return value


def _load_query(
    raw: Any,
    index: int,
    *,
    default_window_minutes: int,
    limit_per_job: int,
    minimum_window_minutes: int,
) -> CampaignQuery:
    context = f"queries[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{context} debe ser un objeto")

    layer = raw.get("corpus_layer", "core")
    if layer not in {"core", "thematic"}:
        raise ValueError(f"{context}: 'corpus_layer' debe ser core o thematic")

    limit = _positive_int(raw, "limit", context, default=limit_per_job)
    minimum_results = raw.get("minimum_results", 0)
    if (
        not isinstance(minimum_results, int)
        or isinstance(minimum_results, bool)
        or minimum_results < 0
        or minimum_results > limit
    ):
        raise ValueError(f"{context}: 'minimum_results' debe estar entre 0 y 'limit'")

    return CampaignQuery(
        label=_text(raw, "label", context),
        text=_text(raw, "text", context),
        corpus_layer=layer,
        window_minutes=_positive_int(
            raw, "window_minutes", context, default=default_window_minutes
        ),
        limit=limit,
        minimum_results=minimum_results,
        minimum_window_minutes=_positive_int(
            raw,
            "minimum_window_minutes",
            context,
            default=minimum_window_minutes,
        ),
    )


def _load_override(raw: Any, index: int, query_labels: set[str]) -> WindowOverride:
    context = f"window_overrides[{index}]"
    if not isinstance(raw, dict):
        raise ValueError(f"{context} debe ser un objeto")

    since = _text(raw, "since", context)
    until = _text(raw, "until", context)
    if _parse_local_boundary(since) >= _parse_local_boundary(until):
        raise ValueError(f"{context}: 'since' debe ser anterior a 'until'")

    families = raw.get("query_families", [])
    if not isinstance(families, list) or any(
        not isinstance(item, str) or not item.strip() for item in families
    ):
        raise ValueError(f"{context}: 'query_families' debe ser una lista de textos")
    cleaned = tuple(item.strip() for item in families)
    unknown = set(cleaned) - query_labels
    if unknown:
        raise ValueError(
            f"{context}: consultas desconocidas: {', '.join(sorted(unknown))}"
        )

    return WindowOverride(
        label=_text(raw, "label", context),
        since=since,
        until=until,
        window_minutes=_positive_int(raw, "window_minutes", context),
        query_families=cleaned,
    )


def load_campaign_config(path: str | Path) -> CampaignConfig:
    campaign_path = Path(path)
    with campaign_path.open(encoding="utf-8") as file:
        raw = json.load(file)
    if not isinstance(raw, dict):
        raise ValueError("La campaña debe ser un objeto JSON")

    timezone = _text(
        raw,
        "timezone",
        "campaña",
        default="America/Argentina/Buenos_Aires",
    )
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Zona horaria desconocida: {timezone}") from error

    since = _text(raw, "since", "campaña")
    until = _text(raw, "until", "campaña")
    start = _parse_local_boundary(since)
    end = _parse_local_boundary(until)
    if start >= end:
        raise ValueError("campaña: 'since' debe ser anterior a 'until'")

    product = raw.get("search_product", "Latest")
    if product not in {"Latest", "Top", "Media"}:
        raise ValueError("'search_product' debe ser Latest, Top o Media")

    default_window = _positive_int(
        raw, "default_window_minutes", "campaña", default=360
    )
    limit_per_job = _positive_int(raw, "limit_per_job", "campaña", default=1000)
    minimum_window = _positive_int(
        raw, "minimum_window_minutes", "campaña", default=10
    )

    raw_queries = raw.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("'queries' debe contener al menos una consulta")
    queries = tuple(
        _load_query(
            item,
            index,
            default_window_minutes=default_window,
            limit_per_job=limit_per_job,
            minimum_window_minutes=minimum_window,
        )
        for index, item in enumerate(raw_queries)
    )
    labels = [query.label for query in queries]
    if len(labels) != len(set(labels)):
        raise ValueError("Cada consulta de campaña debe tener un 'label' único")

    raw_overrides = raw.get("window_overrides", [])
    if not isinstance(raw_overrides, list):
        raise ValueError("'window_overrides' debe ser una lista")
    overrides = tuple(
        _load_override(item, index, set(labels))
        for index, item in enumerate(raw_overrides)
    )
    for override in overrides:
        override_start, override_end = override.boundaries()
        if override_start < start or override_end > end:
            raise ValueError(
                f"window_overrides '{override.label}' debe estar dentro de la campaña"
            )

    return CampaignConfig(
        campaign_id=_text(raw, "campaign_id", "campaña"),
        description=str(raw.get("description", "")).strip(),
        timezone=timezone,
        since=since,
        until=until,
        search_product=product,
        default_window_minutes=default_window,
        limit_per_job=limit_per_job,
        minimum_window_minutes=minimum_window,
        queries=queries,
        overrides=overrides,
    )


def _local_string(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(timespec="seconds")


def _window_label(family: str, start: datetime, end: datetime) -> str:
    return (
        f"{family}__{start.strftime('%Y%m%dT%H%M%S')}"
        f"__{end.strftime('%Y%m%dT%H%M%S')}"
    )


def _matching_overrides(
    campaign: CampaignConfig, query_family: str
) -> tuple[WindowOverride, ...]:
    return tuple(
        override
        for override in campaign.overrides
        if override.applies_to(query_family)
    )


def _next_window_end(
    campaign_end: datetime,
    cursor: datetime,
    default_minutes: int,
    overrides: tuple[WindowOverride, ...],
) -> datetime:
    active = []
    future_boundaries = [campaign_end]
    for override in overrides:
        start, end = override.boundaries()
        if start <= cursor < end:
            active.append(override)
        if cursor < start:
            future_boundaries.append(start)
        if cursor < end:
            future_boundaries.append(end)

    minutes = min(
        [default_minutes, *(override.window_minutes for override in active)]
    )
    proposed = cursor + timedelta(minutes=minutes)
    return min(proposed, *future_boundaries)


def generate_experiment(campaign: CampaignConfig) -> ExperimentConfig:
    campaign_start, campaign_end = campaign.boundaries()
    planned: list[QuerySpec] = []

    for query in campaign.queries:
        cursor = campaign_start
        overrides = _matching_overrides(campaign, query.label)
        while cursor < campaign_end:
            end = _next_window_end(
                campaign_end,
                cursor,
                query.window_minutes,
                overrides,
            )
            if end <= cursor:
                raise RuntimeError(f"No se pudo avanzar el plan para {query.label}")
            planned.append(
                QuerySpec(
                    label=_window_label(query.label, cursor, end),
                    text=query.text,
                    since=_local_string(cursor),
                    until=_local_string(end),
                    limit=query.limit,
                    minimum_results=query.minimum_results,
                    query_family=query.label,
                    corpus_layer=query.corpus_layer,
                    minimum_window_minutes=query.minimum_window_minutes,
                )
            )
            cursor = end

    return ExperimentConfig(
        experiment_id=campaign.campaign_id,
        search_product=campaign.search_product,
        download_replies=False,
        reply_source_limit=0,
        replies_per_tweet=0,
        reply_delay_seconds=0,
        queries=tuple(planned),
        timezone=campaign.timezone,
    )


def generate_thread_experiment(
    roots: list[dict[str, Any]],
    *,
    experiment_id: str,
    since: str,
    until: str,
    timezone: str,
    limit_per_thread: int,
    minimum_window_minutes: int,
    query_family: str,
) -> ExperimentConfig:
    if limit_per_thread <= 0:
        raise ValueError("limit_per_thread debe ser positivo")
    if minimum_window_minutes <= 0:
        raise ValueError("minimum_window_minutes debe ser positivo")
    if _parse_local_boundary(since) >= _parse_local_boundary(until):
        raise ValueError("'since' debe ser anterior a 'until'")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Zona horaria desconocida: {timezone}") from error

    seen: set[str] = set()
    queries: list[QuerySpec] = []
    for root in roots:
        conversation_id = str(root.get("conversation_id") or root.get("tweet_id") or "")
        if not conversation_id or conversation_id in seen:
            continue
        seen.add(conversation_id)
        queries.append(
            QuerySpec(
                label=f"thread__{conversation_id}",
                text=f"conversation_id:{conversation_id}",
                since=since,
                until=until,
                limit=limit_per_thread,
                minimum_results=1,
                query_family=query_family,
                corpus_layer="thread",
                minimum_window_minutes=minimum_window_minutes,
                conversation_id=conversation_id,
            )
        )

    if not queries:
        raise ValueError("No hay conversaciones válidas para expandir")

    return ExperimentConfig(
        experiment_id=experiment_id,
        search_product="Latest",
        download_replies=False,
        reply_source_limit=0,
        replies_per_tweet=0,
        reply_delay_seconds=0,
        queries=tuple(queries),
        timezone=timezone,
    )


def experiment_to_dict(
    experiment: ExperimentConfig,
    *,
    generated_from: str | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "experiment_id": experiment.experiment_id,
        "timezone": experiment.timezone,
        "search_product": experiment.search_product,
        "download_replies": experiment.download_replies,
        "reply_source_limit": experiment.reply_source_limit,
        "replies_per_tweet": experiment.replies_per_tweet,
        "reply_delay_seconds": experiment.reply_delay_seconds,
        "queries": [asdict(query) for query in experiment.queries],
    }
    if generated_from:
        output["generated_from"] = generated_from
    return output


def write_experiment(
    experiment: ExperimentConfig,
    output_path: str | Path,
    *,
    generated_from: str | None = None,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            experiment_to_dict(experiment, generated_from=generated_from),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def select_queries(
    experiment: ExperimentConfig,
    *,
    shard_count: int,
    shard_index: int,
    max_jobs: int | None,
) -> ExperimentConfig:
    if shard_count <= 0:
        raise ValueError("--shard-count debe ser positivo")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("--shard-index debe estar entre 0 y shard-count - 1")
    if max_jobs is not None and max_jobs <= 0:
        raise ValueError("--max-jobs debe ser positivo")

    selected = [
        query
        for position, query in enumerate(experiment.queries)
        if position % shard_count == shard_index
    ]
    if max_jobs is not None:
        selected = selected[:max_jobs]
    return replace(experiment, queries=tuple(selected))


def refine_experiment(
    experiment: ExperimentConfig, saturated_labels: set[str]
) -> ExperimentConfig:
    refined: list[QuerySpec] = []
    for query in experiment.queries:
        if query.label not in saturated_labels:
            continue
        start = _parse_local_boundary(query.since)
        end = _parse_local_boundary(query.until)
        duration = end - start
        minimum = timedelta(minutes=query.minimum_window_minutes)
        if duration < minimum * 2:
            continue
        midpoint = (start + duration / 2).replace(microsecond=0)
        label_family = query.family
        if query.conversation_id:
            label_family = f"{label_family}__conversation_{query.conversation_id}"
        for child_start, child_end in ((start, midpoint), (midpoint, end)):
            refined.append(
                replace(
                    query,
                    label=_window_label(label_family, child_start, child_end),
                    since=_local_string(child_start),
                    until=_local_string(child_end),
                )
            )

    return replace(
        experiment,
        experiment_id=f"{experiment.experiment_id}_refinement",
        queries=tuple(refined),
    )


def plan_metrics(experiment: ExperimentConfig) -> dict[str, Any]:
    by_layer: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for query in experiment.queries:
        by_layer[query.corpus_layer] = by_layer.get(query.corpus_layer, 0) + 1
        by_family[query.family] = by_family.get(query.family, 0) + 1
    return {
        "experiment_id": experiment.experiment_id,
        "jobs": len(experiment.queries),
        "by_layer": dict(sorted(by_layer.items())),
        "by_query_family": dict(sorted(by_family.items())),
    }
