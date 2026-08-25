from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class QuerySpec:
    label: str
    text: str
    since: str
    until: str
    limit: int
    minimum_results: int = 1

    def epoch_bounds(self, timezone_name: str) -> tuple[int, int]:
        timezone = ZoneInfo(timezone_name)
        start = datetime.combine(date.fromisoformat(self.since), time.min, timezone)
        end = datetime.combine(date.fromisoformat(self.until), time.min, timezone)
        return int(start.timestamp()), int(end.timestamp())

    def full_query_for(self, timezone_name: str) -> str:
        start, end = self.epoch_bounds(timezone_name)
        return f"{self.text} since_time:{start} until_time:{end}"


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str
    search_product: str
    download_replies: bool
    reply_source_limit: int
    replies_per_tweet: int
    reply_delay_seconds: float
    queries: tuple[QuerySpec, ...]
    timezone: str = "America/Argentina/Buenos_Aires"


def _required_text(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: '{key}' debe ser un texto no vacío")
    return value.strip()


def _positive_int(data: dict[str, Any], key: str, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{context}: '{key}' debe ser un entero positivo")
    return value


def _parse_query(data: Any, index: int) -> QuerySpec:
    context = f"queries[{index}]"
    if not isinstance(data, dict):
        raise ValueError(f"{context} debe ser un objeto")

    since = _required_text(data, "since", context)
    until = _required_text(data, "until", context)
    since_date = date.fromisoformat(since)
    until_date = date.fromisoformat(until)
    if since_date >= until_date:
        raise ValueError(f"{context}: 'since' debe ser anterior a 'until'")

    limit = _positive_int(data, "limit", context)
    minimum_results = data.get("minimum_results", 1)
    if (
        not isinstance(minimum_results, int)
        or isinstance(minimum_results, bool)
        or minimum_results < 0
        or minimum_results > limit
    ):
        raise ValueError(
            f"{context}: 'minimum_results' debe estar entre 0 y 'limit'"
        )

    return QuerySpec(
        label=_required_text(data, "label", context),
        text=_required_text(data, "text", context),
        since=since,
        until=until,
        limit=limit,
        minimum_results=minimum_results,
    )


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as file:
        raw = json.load(file)

    if not isinstance(raw, dict):
        raise ValueError("La configuración debe ser un objeto JSON")

    raw_queries = raw.get("queries")
    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("'queries' debe contener al menos una consulta")

    queries = tuple(_parse_query(item, index) for index, item in enumerate(raw_queries))
    labels = [query.label for query in queries]
    if len(labels) != len(set(labels)):
        raise ValueError("Cada consulta debe tener un 'label' único")

    product = raw.get("search_product", "Latest")
    if product not in {"Latest", "Top", "Media"}:
        raise ValueError("'search_product' debe ser Latest, Top o Media")

    download_replies = raw.get("download_replies", False)
    if not isinstance(download_replies, bool):
        raise ValueError("'download_replies' debe ser true o false")

    reply_source_limit = raw.get("reply_source_limit", 5)
    replies_per_tweet = raw.get("replies_per_tweet", 25)
    reply_delay_seconds = raw.get("reply_delay_seconds", 2.0)

    if not isinstance(reply_source_limit, int) or reply_source_limit < 0:
        raise ValueError("'reply_source_limit' debe ser un entero no negativo")
    if not isinstance(replies_per_tweet, int) or replies_per_tweet < 0:
        raise ValueError("'replies_per_tweet' debe ser un entero no negativo")
    if not isinstance(reply_delay_seconds, (int, float)) or reply_delay_seconds < 0:
        raise ValueError("'reply_delay_seconds' debe ser un número no negativo")

    timezone_name = raw.get("timezone", "America/Argentina/Buenos_Aires")
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        raise ValueError("'timezone' debe ser un texto no vacío")
    timezone_name = timezone_name.strip()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Zona horaria desconocida: {timezone_name}") from error

    return ExperimentConfig(
        experiment_id=_required_text(raw, "experiment_id", "configuración"),
        search_product=product,
        download_replies=download_replies,
        reply_source_limit=reply_source_limit,
        replies_per_tweet=replies_per_tweet,
        reply_delay_seconds=float(reply_delay_seconds),
        queries=queries,
        timezone=timezone_name,
    )
