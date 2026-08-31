from __future__ import annotations

import csv
import heapq
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TWEET_FIELDS = (
    "tweet_id",
    "username",
    "displayname",
    "date",
    "date_art",
    "text",
    "likes",
    "retweets",
    "replies",
    "quotes",
    "views",
    "conversation_id",
    "in_reply_to",
    "in_reply_to_user",
    "mentioned_users",
    "hashtags",
    "lang",
    "url",
    "capture_search",
    "capture_thread",
    "corpus_role",
    "thread_occurrences",
    "thread_conversation_count",
    "in_original_query_day_utc",
    "in_research_day_art",
    "mentions_argentina",
    "matches_any_configured_text",
    "is_conversation_root",
    "root_status",
    "parent_status",
)

ENGAGEMENT_FIELDS = (
    "tweet_id",
    "date_art",
    "username",
    "text",
    "interaction_total",
    "likes",
    "retweets",
    "replies",
    "quotes",
    "views",
    "corpus_role",
    "capture_search",
    "capture_thread",
    "mentions_argentina",
    "in_research_day_art",
    "is_conversation_root",
    "conversation_id",
    "url",
)


def _read_jsonl(path: Path, counters: dict[str, int]) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            counters["lines"] += 1
            if not line.strip():
                counters["blank_lines"] += 1
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                counters["invalid_json"] += 1
                continue
            if not isinstance(item, dict):
                counters["invalid_records"] += 1
                continue
            item["_source_line"] = line_number
            counters["valid_records"] += 1
            yield item


def _identifier(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _json_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).casefold().strip()


def _text_flags(text: Any) -> tuple[bool, bool]:
    normalized = _normalize_text(text)
    mentions_argentina = bool(re.search(r"\bargentin(?:a|o|as|os)\b", normalized))
    phrases = (
        "espana argentina",
        "argentina espana",
        "argentina campeon",
    )
    return mentions_argentina, mentions_argentina or any(phrase in normalized for phrase in phrases)


def _normalize_tweet(raw: dict[str, Any], timezone: ZoneInfo) -> dict[str, Any] | None:
    tweet_id = _identifier(raw.get("tweet_id"))
    if not tweet_id:
        return None
    created_at = _timestamp(raw.get("date"))
    mentions_argentina, matches_any = _text_flags(raw.get("text"))
    return {
        "tweet_id": tweet_id,
        "username": str(raw.get("username") or ""),
        "displayname": str(raw.get("displayname") or ""),
        "date": created_at.isoformat() if created_at else "",
        "date_art": created_at.astimezone(timezone).isoformat() if created_at else "",
        "text": str(raw.get("text") or ""),
        "likes": _integer(raw.get("likes")),
        "retweets": _integer(raw.get("retweets")),
        "replies": _integer(raw.get("replies")),
        "quotes": _integer(raw.get("quotes")),
        "views": _integer(raw.get("views")),
        "conversation_id": _identifier(raw.get("conversation_id")),
        "in_reply_to": _identifier(raw.get("in_reply_to")),
        "in_reply_to_user": str(raw.get("in_reply_to_user") or ""),
        "mentioned_users": _json_list(raw.get("mentioned_users")),
        "hashtags": _json_list(raw.get("hashtags")),
        "lang": str(raw.get("lang") or ""),
        "url": str(raw.get("url") or ""),
        "_datetime": created_at,
        "mentions_argentina": mentions_argentina,
        "matches_any_configured_text": matches_any,
    }


def _in_window(value: datetime | None, start: datetime, end: datetime) -> bool:
    return value is not None and start <= value < end


def _gini(values: list[int]) -> float:
    positive = sorted(value for value in values if value >= 0)
    if not positive or sum(positive) == 0:
        return 0.0
    count = len(positive)
    weighted = sum((index + 1) * value for index, value in enumerate(positive))
    return (2 * weighted) / (count * sum(positive)) - (count + 1) / count


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            output = dict(row)
            for key, value in output.items():
                if isinstance(value, (list, tuple, dict)):
                    output[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow(output)


def _write_parquet(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bool:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_rows = [{field: row.get(field) for field in fields} for row in rows]
    pq.write_table(pa.Table.from_pylist(clean_rows), path, compression="zstd")
    return True


def _hour_key(value: datetime, timezone: ZoneInfo) -> datetime:
    return value.astimezone(timezone).replace(minute=0, second=0, microsecond=0)


def _interaction_total(row: dict[str, Any]) -> int:
    return sum(int(row.get(field) or 0) for field in ("likes", "retweets", "replies", "quotes"))


def audit_external_jsonl(
    tweets_path: str | Path,
    threads_path: str | Path,
    output_dir: str | Path,
    *,
    target_date: str = "2026-07-19",
    timezone_name: str = "America/Argentina/Buenos_Aires",
) -> dict[str, Any]:
    tweets_source = Path(tweets_path)
    threads_source = Path(threads_path)
    destination = Path(output_dir)
    if not tweets_source.exists():
        raise FileNotFoundError(f"No existe {tweets_source}")
    if not threads_source.exists():
        raise FileNotFoundError(f"No existe {threads_source}")

    target = date.fromisoformat(target_date)
    timezone = ZoneInfo(timezone_name)
    query_start = datetime.combine(target, time.min, tzinfo=UTC)
    query_end = query_start + timedelta(days=1)
    local_start = datetime.combine(target, time.min, tzinfo=timezone)
    local_end = local_start + timedelta(days=1)
    local_start_utc = local_start.astimezone(UTC)
    local_end_utc = local_end.astimezone(UTC)

    tweet_file_stats = defaultdict(int)
    thread_file_stats = defaultdict(int)
    direct: dict[str, dict[str, Any]] = {}
    direct_occurrences = Counter()
    invalid_tweets = 0
    for raw in _read_jsonl(tweets_source, tweet_file_stats):
        tweet = _normalize_tweet(raw, timezone)
        if tweet is None:
            invalid_tweets += 1
            continue
        direct_occurrences[tweet["tweet_id"]] += 1
        direct.setdefault(tweet["tweet_id"], tweet)

    thread_canonical: dict[str, dict[str, Any]] = {}
    thread_occurrences = Counter()
    tweet_conversations: dict[str, set[str]] = defaultdict(set)
    parent_statuses: dict[tuple[str, str], str] = {}
    conversation_rows: list[dict[str, Any]] = []
    conversation_ids_seen = Counter()
    invalid_thread_tweets = 0

    for raw_thread in _read_jsonl(threads_source, thread_file_stats):
        conversation_id = _identifier(raw_thread.get("conversation_id"))
        conversation_ids_seen[conversation_id] += 1
        raw_tweets = raw_thread.get("tweets")
        if not isinstance(raw_tweets, list):
            raw_tweets = []

        normalized: list[dict[str, Any]] = []
        for raw_tweet in raw_tweets:
            if not isinstance(raw_tweet, dict):
                invalid_thread_tweets += 1
                continue
            tweet = _normalize_tweet(raw_tweet, timezone)
            if tweet is None:
                invalid_thread_tweets += 1
                continue
            normalized.append(tweet)
            tweet_id = tweet["tweet_id"]
            thread_occurrences[tweet_id] += 1
            tweet_conversations[tweet_id].add(conversation_id)
            thread_canonical.setdefault(tweet_id, tweet)

        ids = {tweet["tweet_id"] for tweet in normalized}
        root_count = sum(tweet["tweet_id"] == conversation_id for tweet in normalized)
        if not conversation_id:
            root_status = "invalid_conversation_id"
        elif root_count == 0:
            root_status = "root_missing"
        elif root_count == 1:
            root_status = "root_present"
        else:
            root_status = "root_duplicated"

        missing_parents = 0
        replies = 0
        for tweet in normalized:
            parent = tweet["in_reply_to"]
            if not parent:
                status = "no_parent"
            elif parent in ids:
                status = "parent_present"
                replies += 1
            else:
                status = "parent_missing"
                missing_parents += 1
                replies += 1
            parent_statuses[(conversation_id, tweet["tweet_id"])] = status

        dates = [tweet["_datetime"] for tweet in normalized if tweet["_datetime"]]
        unique_count = len(ids)
        conversation_rows.append(
            {
                "conversation_id": conversation_id,
                "tweet_occurrences": len(normalized),
                "unique_tweets": unique_count,
                "duplicates_within_conversation": len(normalized) - unique_count,
                "root_status": root_status,
                "root_count": root_count,
                "first_tweet_id": normalized[0]["tweet_id"] if normalized else "",
                "first_is_root": bool(normalized and normalized[0]["tweet_id"] == conversation_id),
                "reply_tweets": replies,
                "missing_parent_tweets": missing_parents,
                "has_direct_search_seed": any(
                    tweet_id in direct for tweet_id in ids
                ),
                "direct_seed_count": sum(tweet_id in direct for tweet_id in ids),
                "tweets_in_original_query_day_utc": sum(
                    _in_window(tweet["_datetime"], query_start, query_end)
                    for tweet in normalized
                ),
                "tweets_in_research_day_art": sum(
                    _in_window(tweet["_datetime"], local_start_utc, local_end_utc)
                    for tweet in normalized
                ),
                "tweets_mentioning_argentina": sum(
                    tweet["mentions_argentina"] for tweet in normalized
                ),
                "date_min_utc": min(dates).isoformat() if dates else "",
                "date_max_utc": max(dates).isoformat() if dates else "",
            }
        )

    root_status_by_conversation = {
        row["conversation_id"]: row["root_status"] for row in conversation_rows
    }
    union_ids = set(direct) | set(thread_canonical)
    clean_rows: list[dict[str, Any]] = []
    for tweet_id in sorted(
        union_ids,
        key=lambda identifier: (
            (direct.get(identifier) or thread_canonical[identifier]).get("date", ""),
            identifier,
        ),
    ):
        canonical = dict(direct.get(tweet_id) or thread_canonical[tweet_id])
        created_at = canonical.pop("_datetime")
        conversation_id = canonical["conversation_id"]
        memberships = tweet_conversations.get(tweet_id, set())
        membership = (
            conversation_id
            if conversation_id in memberships
            else next(iter(memberships), "")
        )
        canonical.update(
            {
                "capture_search": tweet_id in direct,
                "capture_thread": tweet_id in thread_canonical,
                "corpus_role": (
                    "search_return" if tweet_id in direct else "thread_context_only"
                ),
                "thread_occurrences": thread_occurrences[tweet_id],
                "thread_conversation_count": len(memberships),
                "in_original_query_day_utc": _in_window(created_at, query_start, query_end),
                "in_research_day_art": _in_window(created_at, local_start_utc, local_end_utc),
                "is_conversation_root": bool(
                    conversation_id and tweet_id == conversation_id
                ),
                "root_status": root_status_by_conversation.get(
                    conversation_id, "conversation_not_expanded"
                ),
                "parent_status": parent_statuses.get(
                    (membership, tweet_id), "not_audited_in_thread"
                ),
            }
        )
        clean_rows.append(canonical)

    conversation_rows.sort(
        key=lambda row: (-row["unique_tweets"], row["conversation_id"])
    )
    total_conversation_tweets = sum(row["unique_tweets"] for row in conversation_rows)
    cumulative = 0
    concentration_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(conversation_rows, start=1):
        cumulative += row["unique_tweets"]
        concentration_rows.append(
            {
                "rank": rank,
                "conversation_id": row["conversation_id"],
                "unique_tweets": row["unique_tweets"],
                "share": row["unique_tweets"] / total_conversation_tweets
                if total_conversation_tweets
                else 0,
                "cumulative_share": cumulative / total_conversation_tweets
                if total_conversation_tweets
                else 0,
                "root_status": row["root_status"],
            }
        )

    hourly_direct = Counter()
    hourly_thread = Counter()
    hourly_union = Counter()
    hourly_thread_argentina = Counter()
    for tweet in direct.values():
        if tweet["_datetime"]:
            hourly_direct[_hour_key(tweet["_datetime"], timezone)] += 1
    for tweet in thread_canonical.values():
        if tweet["_datetime"]:
            hour = _hour_key(tweet["_datetime"], timezone)
            hourly_thread[hour] += 1
            if tweet["mentions_argentina"]:
                hourly_thread_argentina[hour] += 1
    for row in clean_rows:
        created_at = _timestamp(row["date"])
        if created_at:
            hourly_union[_hour_key(created_at, timezone)] += 1

    all_hours = sorted(set(hourly_direct) | set(hourly_thread) | set(hourly_union))
    hourly_all_rows = [
        {
            "hour_start_art": hour.isoformat(),
            "direct_search_unique": hourly_direct[hour],
            "thread_unique": hourly_thread[hour],
            "thread_unique_mentioning_argentina": hourly_thread_argentina[hour],
            "union_unique": hourly_union[hour],
        }
        for hour in all_hours
    ]
    hourly_day_rows = []
    for hour_index in range(24):
        hour = local_start + timedelta(hours=hour_index)
        hourly_day_rows.append(
            {
                "hour_start_art": hour.isoformat(),
                "direct_search_unique": hourly_direct[hour],
                "thread_unique": hourly_thread[hour],
                "thread_unique_mentioning_argentina": hourly_thread_argentina[hour],
                "union_unique": hourly_union[hour],
            }
        )

    root_counts = Counter(row["root_status"] for row in conversation_rows)
    sizes = [row["unique_tweets"] for row in conversation_rows]
    thread_unique_total = len(thread_canonical)
    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "inputs": {
            "tweets_path": str(tweets_source),
            "threads_path": str(threads_source),
            "tweets_file": dict(tweet_file_stats),
            "threads_file": dict(thread_file_stats),
            "invalid_tweets": invalid_tweets,
            "invalid_thread_tweets": invalid_thread_tweets,
        },
        "window_definitions": {
            "original_query_day_utc": [query_start.isoformat(), query_end.isoformat()],
            "research_day_art": [local_start.isoformat(), local_end.isoformat()],
        },
        "volume": {
            "direct_occurrences": sum(direct_occurrences.values()),
            "direct_unique": len(direct),
            "direct_duplicate_occurrences": sum(direct_occurrences.values()) - len(direct),
            "conversation_records": len(conversation_rows),
            "conversation_ids_unique": len({row["conversation_id"] for row in conversation_rows}),
            "duplicate_conversation_records": sum(conversation_ids_seen.values())
            - len(conversation_ids_seen),
            "thread_tweet_occurrences": sum(thread_occurrences.values()),
            "thread_unique": thread_unique_total,
            "thread_duplicate_occurrences": sum(thread_occurrences.values())
            - thread_unique_total,
            "direct_thread_overlap": len(set(direct) & set(thread_canonical)),
            "union_unique": len(clean_rows),
            "thread_only_unique": len(set(thread_canonical) - set(direct)),
        },
        "temporal": {
            "direct_in_original_query_day_utc": sum(
                _in_window(tweet["_datetime"], query_start, query_end)
                for tweet in direct.values()
            ),
            "direct_in_research_day_art": sum(
                _in_window(tweet["_datetime"], local_start_utc, local_end_utc)
                for tweet in direct.values()
            ),
            "thread_unique_in_original_query_day_utc": sum(
                _in_window(tweet["_datetime"], query_start, query_end)
                for tweet in thread_canonical.values()
            ),
            "thread_unique_in_research_day_art": sum(
                _in_window(tweet["_datetime"], local_start_utc, local_end_utc)
                for tweet in thread_canonical.values()
            ),
            "thread_unique_outside_research_day_art": sum(
                not _in_window(tweet["_datetime"], local_start_utc, local_end_utc)
                for tweet in thread_canonical.values()
            ),
            "date_min_utc": min(
                (row["date"] for row in clean_rows if row["date"]), default=""
            ),
            "date_max_utc": max(
                (row["date"] for row in clean_rows if row["date"]), default=""
            ),
        },
        "content": {
            "direct_mentioning_argentina": sum(
                tweet["mentions_argentina"] for tweet in direct.values()
            ),
            "thread_unique_mentioning_argentina": sum(
                tweet["mentions_argentina"] for tweet in thread_canonical.values()
            ),
            "thread_unique_not_mentioning_argentina": sum(
                not tweet["mentions_argentina"] for tweet in thread_canonical.values()
            ),
        },
        "roots_and_links": {
            **dict(sorted(root_counts.items())),
            "first_record_is_root": sum(row["first_is_root"] for row in conversation_rows),
            "conversations_with_missing_parents": sum(
                row["missing_parent_tweets"] > 0 for row in conversation_rows
            ),
            "missing_parent_tweets": sum(
                row["missing_parent_tweets"] for row in conversation_rows
            ),
        },
        "concentration": {
            "largest_conversation_unique_tweets": max(sizes, default=0),
            "median_conversation_unique_tweets": (
                sorted(sizes)[len(sizes) // 2] if sizes else 0
            ),
            "top_10_share": sum(sorted(sizes, reverse=True)[:10])
            / total_conversation_tweets
            if total_conversation_tweets
            else 0,
            "top_50_share": sum(sorted(sizes, reverse=True)[:50]) / total_conversation_tweets
            if total_conversation_tweets
            else 0,
            "top_100_share": sum(sorted(sizes, reverse=True)[:100])
            / total_conversation_tweets
            if total_conversation_tweets
            else 0,
            "gini_conversation_size": _gini(sizes),
            "hhi_conversation_size": sum(
                math.pow(size / total_conversation_tweets, 2) for size in sizes
            )
            if total_conversation_tweets
            else 0,
        },
    }
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(destination / "tweets_clean.csv", clean_rows, TWEET_FIELDS)
    search_rows = [row for row in clean_rows if row["capture_search"]]
    _write_csv(destination / "search_returns.csv", search_rows, TWEET_FIELDS)
    _write_csv(
        destination / "search_returns_research_day_art.csv",
        [row for row in search_rows if row["in_research_day_art"]],
        TWEET_FIELDS,
    )
    top_engagement = heapq.nlargest(500, clean_rows, key=_interaction_total)
    engagement_rows = []
    for row in top_engagement:
        output = dict(row)
        output["interaction_total"] = _interaction_total(row)
        engagement_rows.append(output)
    _write_csv(
        destination / "top_engagement_review.csv",
        engagement_rows,
        ENGAGEMENT_FIELDS,
    )
    conversation_fields = tuple(conversation_rows[0].keys()) if conversation_rows else ()
    _write_csv(destination / "conversations_audit.csv", conversation_rows, conversation_fields)
    concentration_fields = tuple(concentration_rows[0].keys()) if concentration_rows else ()
    _write_csv(
        destination / "conversation_concentration.csv",
        concentration_rows,
        concentration_fields,
    )
    hourly_fields = (
        "hour_start_art",
        "direct_search_unique",
        "thread_unique",
        "thread_unique_mentioning_argentina",
        "union_unique",
    )
    _write_csv(destination / "hourly_research_day_art.csv", hourly_day_rows, hourly_fields)
    _write_csv(destination / "hourly_all_observed.csv", hourly_all_rows, hourly_fields)
    missing_roots = [row for row in conversation_rows if row["root_status"] == "root_missing"]
    _write_csv(destination / "missing_roots.csv", missing_roots, conversation_fields)
    parquet_written = _write_parquet(
        destination / "tweets_clean.parquet", clean_rows, TWEET_FIELDS
    )
    summary["outputs"] = {
        "directory": str(destination),
        "parquet_written": parquet_written,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
