from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import ExperimentConfig, QuerySpec
from .models import NormalizedTweet

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    display_name TEXT,
    description TEXT,
    created_at TEXT,
    location TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    statuses_count INTEGER,
    favourites_count INTEGER,
    listed_count INTEGER,
    media_count INTEGER,
    protected INTEGER,
    verified INTEGER,
    blue INTEGER,
    blue_type TEXT,
    profile_image_url TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_snapshots (
    user_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    username TEXT,
    display_name TEXT,
    description TEXT,
    created_at TEXT,
    location TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    statuses_count INTEGER,
    favourites_count INTEGER,
    listed_count INTEGER,
    media_count INTEGER,
    protected INTEGER,
    verified INTEGER,
    blue INTEGER,
    blue_type TEXT,
    profile_image_url TEXT,
    PRIMARY KEY (user_id, snapshot_date),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS tweets (
    tweet_id TEXT PRIMARY KEY,
    created_at TEXT,
    text TEXT NOT NULL,
    language TEXT,
    url TEXT,
    author_id TEXT,
    like_count INTEGER,
    retweet_count INTEGER,
    reply_count INTEGER,
    quote_count INTEGER,
    view_count INTEGER,
    conversation_id TEXT,
    reply_to_tweet_id TEXT,
    reply_to_user_id TEXT,
    reply_to_username TEXT,
    quoted_tweet_id TEXT,
    quoted_user_id TEXT,
    quoted_username TEXT,
    retweeted_tweet_id TEXT,
    retweeted_user_id TEXT,
    retweeted_username TEXT,
    hashtags_json TEXT NOT NULL,
    cashtags_json TEXT NOT NULL DEFAULT '[]',
    mentioned_user_ids_json TEXT NOT NULL DEFAULT '[]',
    mentioned_usernames_json TEXT NOT NULL DEFAULT '[]',
    links_json TEXT NOT NULL DEFAULT '[]',
    media_json TEXT NOT NULL DEFAULT '[]',
    source_label TEXT,
    possibly_sensitive INTEGER,
    place_full_name TEXT,
    place_country TEXT,
    place_country_code TEXT,
    longitude REAL,
    latitude REAL,
    captured_at TEXT NOT NULL,
    source_provider TEXT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    query_label TEXT NOT NULL,
    query_family TEXT NOT NULL DEFAULT '',
    corpus_layer TEXT NOT NULL DEFAULT 'core',
    query_text TEXT NOT NULL,
    since_date TEXT NOT NULL,
    until_date TEXT NOT NULL,
    full_query TEXT NOT NULL,
    target_limit INTEGER NOT NULL,
    search_product TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    search_count INTEGER NOT NULL DEFAULT 0,
    unique_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    saturated INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    machine TEXT,
    twscrape_version TEXT,
    UNIQUE (experiment_id, query_label, since_date, until_date)
);

CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    tweet_id TEXT NOT NULL,
    capture_kind TEXT NOT NULL,
    root_tweet_id TEXT NOT NULL DEFAULT '',
    captured_at TEXT NOT NULL,
    UNIQUE (job_id, tweet_id, capture_kind, root_tweet_id),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id)
);

CREATE TABLE IF NOT EXISTS relationships (
    source_tweet_id TEXT NOT NULL,
    target_tweet_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    source_user_id TEXT,
    target_user_id TEXT,
    target_username TEXT,
    PRIMARY KEY (source_tweet_id, target_tweet_id, relationship_type),
    FOREIGN KEY (source_tweet_id) REFERENCES tweets(tweet_id)
);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);

CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at);
CREATE INDEX IF NOT EXISTS idx_tweets_author_id ON tweets(author_id);
CREATE INDEX IF NOT EXISTS idx_tweets_conversation_id ON tweets(conversation_id);
CREATE INDEX IF NOT EXISTS idx_captures_job_id ON captures(job_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_tweet_id);
"""

MIGRATION_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "description": "TEXT",
        "created_at": "TEXT",
        "location": "TEXT",
        "followers_count": "INTEGER",
        "following_count": "INTEGER",
        "statuses_count": "INTEGER",
        "favourites_count": "INTEGER",
        "listed_count": "INTEGER",
        "media_count": "INTEGER",
        "protected": "INTEGER",
        "verified": "INTEGER",
        "blue": "INTEGER",
        "blue_type": "TEXT",
        "profile_image_url": "TEXT",
    },
    "tweets": {
        "cashtags_json": "TEXT NOT NULL DEFAULT '[]'",
        "mentioned_user_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        "mentioned_usernames_json": "TEXT NOT NULL DEFAULT '[]'",
        "links_json": "TEXT NOT NULL DEFAULT '[]'",
        "media_json": "TEXT NOT NULL DEFAULT '[]'",
        "source_label": "TEXT",
        "possibly_sensitive": "INTEGER",
        "place_full_name": "TEXT",
        "place_country": "TEXT",
        "place_country_code": "TEXT",
        "longitude": "REAL",
        "latitude": "REAL",
    },
    "jobs": {
        "query_family": "TEXT NOT NULL DEFAULT ''",
        "corpus_layer": "TEXT NOT NULL DEFAULT 'core'",
        "search_count": "INTEGER NOT NULL DEFAULT 0",
        "saturated": "INTEGER NOT NULL DEFAULT 0",
    },
}

THREAD_EXPORT_FIELDS = (
    "conversation_id",
    "thread_depth",
    "tweet_id",
    "created_at",
    "text",
    "author_id",
    "author_username",
    "author_display_name",
    "like_count",
    "retweet_count",
    "reply_count",
    "reply_to_tweet_id",
    "reply_to_user_id",
    "reply_to_username",
    "quoted_tweet_id",
    "quoted_user_id",
    "quoted_username",
    "quote_count",
    "view_count",
    "capture_kind",
    "download_root_tweet_id",
    "parent_in_dataset",
    "root_in_dataset",
    "language",
    "url",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def make_job_id(experiment: ExperimentConfig, query: QuerySpec) -> str:
    identity = "\x1f".join(
        [
            experiment.experiment_id,
            experiment.timezone,
            query.label,
            query.text,
            query.since,
            query.until,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


class ResearchStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as database:
            database.executescript(SCHEMA)
            self._migrate_columns(database)
            database.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_layer_family "
                "ON jobs(corpus_layer, query_family)"
            )

    def _migrate_columns(self, database: sqlite3.Connection) -> None:
        for table, columns in MIGRATION_COLUMNS.items():
            existing = {
                row["name"]
                for row in database.execute(f"PRAGMA table_info('{table}')").fetchall()
            }
            for column, definition in columns.items():
                if column not in existing:
                    database.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )

    def prepare_job(
        self,
        experiment: ExperimentConfig,
        query: QuerySpec,
        *,
        machine: str,
        twscrape_version: str,
        force: bool = False,
    ) -> tuple[str, bool]:
        job_id = make_job_id(experiment, query)
        now = utc_now()

        with self.connect() as database:
            database.execute(
                """
                INSERT OR IGNORE INTO jobs (
                    job_id, experiment_id, query_label, query_family,
                    corpus_layer, query_text,
                    since_date, until_date, full_query, target_limit,
                    search_product, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    job_id,
                    experiment.experiment_id,
                    query.label,
                    query.family,
                    query.corpus_layer,
                    query.text,
                    query.since,
                    query.until,
                    query.full_query_for(experiment.timezone),
                    query.limit,
                    experiment.search_product,
                ),
            )
            current = database.execute(
                "SELECT status FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if current is not None and current["status"] == "completed" and not force:
                return job_id, False

            database.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    started_at = ?,
                    finished_at = NULL,
                    attempt_count = attempt_count + 1,
                    fetched_count = 0,
                    search_count = 0,
                    duplicate_count = 0,
                    warning_count = 0,
                    saturated = 0,
                    error_message = NULL,
                    machine = ?,
                    twscrape_version = ?
                WHERE job_id = ?
                """,
                (now, machine, twscrape_version, job_id),
            )

        return job_id, True

    def record_tweet(
        self,
        job_id: str,
        tweet: NormalizedTweet,
        *,
        capture_kind: str,
        root_tweet_id: str | None = None,
    ) -> bool:
        if not tweet.tweet_id:
            raise ValueError("No se puede guardar un tuit sin ID")

        root = root_tweet_id or ""
        with self.connect() as database:
            self._upsert_user(database, tweet)
            self._upsert_tweet(database, tweet)
            cursor = database.execute(
                """
                INSERT OR IGNORE INTO captures (
                    job_id, tweet_id, capture_kind, root_tweet_id, captured_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, tweet.tweet_id, capture_kind, root, tweet.captured_at),
            )
            self._upsert_relationships(database, tweet)
            return cursor.rowcount == 1

    def _upsert_user(self, database: sqlite3.Connection, tweet: NormalizedTweet) -> None:
        if not tweet.author_id:
            return
        profile_values = (
            tweet.author_id,
            tweet.author_username,
            tweet.author_display_name,
            tweet.author_description,
            tweet.author_created_at,
            tweet.author_location,
            tweet.author_followers_count,
            tweet.author_following_count,
            tweet.author_statuses_count,
            tweet.author_favourites_count,
            tweet.author_listed_count,
            tweet.author_media_count,
            tweet.author_protected,
            tweet.author_verified,
            tweet.author_blue,
            tweet.author_blue_type,
            tweet.author_profile_image_url,
        )
        database.execute(
            """
            INSERT INTO users (
                user_id, username, display_name, description, created_at, location,
                followers_count, following_count, statuses_count, favourites_count,
                listed_count, media_count, protected, verified, blue, blue_type,
                profile_image_url, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                display_name = COALESCE(excluded.display_name, users.display_name),
                description = COALESCE(excluded.description, users.description),
                created_at = COALESCE(excluded.created_at, users.created_at),
                location = COALESCE(excluded.location, users.location),
                followers_count = COALESCE(excluded.followers_count, users.followers_count),
                following_count = COALESCE(excluded.following_count, users.following_count),
                statuses_count = COALESCE(excluded.statuses_count, users.statuses_count),
                favourites_count = COALESCE(
                    excluded.favourites_count, users.favourites_count
                ),
                listed_count = COALESCE(excluded.listed_count, users.listed_count),
                media_count = COALESCE(excluded.media_count, users.media_count),
                protected = COALESCE(excluded.protected, users.protected),
                verified = COALESCE(excluded.verified, users.verified),
                blue = COALESCE(excluded.blue, users.blue),
                blue_type = COALESCE(excluded.blue_type, users.blue_type),
                profile_image_url = COALESCE(
                    excluded.profile_image_url, users.profile_image_url
                ),
                last_seen_at = excluded.last_seen_at
            """,
            (*profile_values, tweet.captured_at, tweet.captured_at),
        )
        database.execute(
            """
            INSERT INTO user_snapshots (
                user_id, snapshot_date, observed_at, username, display_name,
                description, created_at, location, followers_count, following_count,
                statuses_count, favourites_count, listed_count, media_count,
                protected, verified, blue, blue_type, profile_image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, snapshot_date) DO UPDATE SET
                observed_at = excluded.observed_at,
                username = COALESCE(excluded.username, user_snapshots.username),
                display_name = COALESCE(
                    excluded.display_name, user_snapshots.display_name
                ),
                description = COALESCE(excluded.description, user_snapshots.description),
                location = COALESCE(excluded.location, user_snapshots.location),
                followers_count = COALESCE(
                    excluded.followers_count, user_snapshots.followers_count
                ),
                following_count = COALESCE(
                    excluded.following_count, user_snapshots.following_count
                ),
                statuses_count = COALESCE(
                    excluded.statuses_count, user_snapshots.statuses_count
                ),
                favourites_count = COALESCE(
                    excluded.favourites_count, user_snapshots.favourites_count
                ),
                listed_count = COALESCE(
                    excluded.listed_count, user_snapshots.listed_count
                ),
                media_count = COALESCE(
                    excluded.media_count, user_snapshots.media_count
                ),
                protected = COALESCE(excluded.protected, user_snapshots.protected),
                verified = COALESCE(excluded.verified, user_snapshots.verified),
                blue = COALESCE(excluded.blue, user_snapshots.blue),
                blue_type = COALESCE(excluded.blue_type, user_snapshots.blue_type),
                profile_image_url = COALESCE(
                    excluded.profile_image_url, user_snapshots.profile_image_url
                )
            """,
            (
                tweet.author_id,
                tweet.captured_at[:10],
                tweet.captured_at,
                *profile_values[1:],
            ),
        )

    def _upsert_tweet(self, database: sqlite3.Connection, tweet: NormalizedTweet) -> None:
        database.execute(
            """
            INSERT INTO tweets (
                tweet_id, created_at, text, language, url, author_id,
                like_count, retweet_count, reply_count, quote_count, view_count,
                conversation_id, reply_to_tweet_id, reply_to_user_id,
                reply_to_username, quoted_tweet_id, quoted_user_id,
                quoted_username, retweeted_tweet_id, retweeted_user_id,
                retweeted_username, hashtags_json, cashtags_json,
                mentioned_user_ids_json, mentioned_usernames_json, links_json,
                media_json, source_label, possibly_sensitive, place_full_name,
                place_country, place_country_code, longitude, latitude,
                captured_at, source_provider
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(tweet_id) DO UPDATE SET
                text = excluded.text,
                like_count = excluded.like_count,
                retweet_count = excluded.retweet_count,
                reply_count = excluded.reply_count,
                quote_count = excluded.quote_count,
                view_count = excluded.view_count,
                conversation_id = COALESCE(excluded.conversation_id, tweets.conversation_id),
                reply_to_tweet_id = COALESCE(excluded.reply_to_tweet_id, tweets.reply_to_tweet_id),
                quoted_tweet_id = COALESCE(excluded.quoted_tweet_id, tweets.quoted_tweet_id),
                retweeted_tweet_id = COALESCE(
                    excluded.retweeted_tweet_id, tweets.retweeted_tweet_id
                ),
                hashtags_json = excluded.hashtags_json,
                cashtags_json = excluded.cashtags_json,
                mentioned_user_ids_json = excluded.mentioned_user_ids_json,
                mentioned_usernames_json = excluded.mentioned_usernames_json,
                links_json = excluded.links_json,
                media_json = excluded.media_json,
                source_label = COALESCE(excluded.source_label, tweets.source_label),
                possibly_sensitive = COALESCE(
                    excluded.possibly_sensitive, tweets.possibly_sensitive
                ),
                place_full_name = COALESCE(
                    excluded.place_full_name, tweets.place_full_name
                ),
                place_country = COALESCE(excluded.place_country, tweets.place_country),
                place_country_code = COALESCE(
                    excluded.place_country_code, tweets.place_country_code
                ),
                longitude = COALESCE(excluded.longitude, tweets.longitude),
                latitude = COALESCE(excluded.latitude, tweets.latitude),
                captured_at = excluded.captured_at
            """,
            (
                tweet.tweet_id,
                tweet.created_at,
                tweet.text,
                tweet.language,
                tweet.url,
                tweet.author_id,
                tweet.like_count,
                tweet.retweet_count,
                tweet.reply_count,
                tweet.quote_count,
                tweet.view_count,
                tweet.conversation_id,
                tweet.reply_to_tweet_id,
                tweet.reply_to_user_id,
                tweet.reply_to_username,
                tweet.quoted_tweet_id,
                tweet.quoted_user_id,
                tweet.quoted_username,
                tweet.retweeted_tweet_id,
                tweet.retweeted_user_id,
                tweet.retweeted_username,
                json.dumps(tweet.hashtags, ensure_ascii=False),
                json.dumps(tweet.cashtags, ensure_ascii=False),
                json.dumps(tweet.mentioned_user_ids, ensure_ascii=False),
                json.dumps(tweet.mentioned_usernames, ensure_ascii=False),
                json.dumps(tweet.links, ensure_ascii=False),
                json.dumps(tweet.media, ensure_ascii=False),
                tweet.source_label,
                tweet.possibly_sensitive,
                tweet.place_full_name,
                tweet.place_country,
                tweet.place_country_code,
                tweet.longitude,
                tweet.latitude,
                tweet.captured_at,
                tweet.source_provider,
            ),
        )

    def _upsert_relationships(self, database: sqlite3.Connection, tweet: NormalizedTweet) -> None:
        relationships = (
            (
                "reply",
                tweet.reply_to_tweet_id,
                tweet.reply_to_user_id,
                tweet.reply_to_username,
            ),
            (
                "quote",
                tweet.quoted_tweet_id,
                tweet.quoted_user_id,
                tweet.quoted_username,
            ),
            (
                "retweet",
                tweet.retweeted_tweet_id,
                tweet.retweeted_user_id,
                tweet.retweeted_username,
            ),
        )
        for relationship_type, target_tweet_id, target_user_id, target_username in relationships:
            if not target_tweet_id:
                continue
            database.execute(
                """
                INSERT OR IGNORE INTO relationships (
                    source_tweet_id, target_tweet_id, relationship_type,
                    source_user_id, target_user_id, target_username
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tweet.tweet_id,
                    target_tweet_id,
                    relationship_type,
                    tweet.author_id,
                    target_user_id,
                    target_username,
                ),
            )

    def add_event(self, job_id: str, level: str, message: str) -> None:
        with self.connect() as database:
            database.execute(
                """
                INSERT INTO job_events (job_id, occurred_at, level, message)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, utc_now(), level, message),
            )

    def finish_job(
        self,
        job_id: str,
        *,
        status: str,
        fetched_count: int,
        duplicate_count: int,
        warning_count: int,
        search_count: int | None = None,
        saturated: bool = False,
        error_message: str | None = None,
    ) -> None:
        if status not in {"completed", "failed"}:
            raise ValueError("El estado final debe ser completed o failed")

        with self.connect() as database:
            counts = database.execute(
                """
                SELECT
                    COUNT(DISTINCT tweet_id) AS unique_count,
                    COUNT(DISTINCT CASE WHEN capture_kind = 'reply' THEN tweet_id END)
                        AS reply_count
                FROM captures
                WHERE job_id = ?
                """,
                (job_id,),
            ).fetchone()
            database.execute(
                """
                UPDATE jobs
                SET status = ?, finished_at = ?, fetched_count = ?, search_count = ?,
                    unique_count = ?, duplicate_count = ?, reply_count = ?,
                    warning_count = ?, saturated = ?, error_message = ?
                WHERE job_id = ?
                """,
                (
                    status,
                    utc_now(),
                    fetched_count,
                    search_count
                    if search_count is not None
                    else max(0, counts["unique_count"] - counts["reply_count"]),
                    counts["unique_count"],
                    duplicate_count,
                    counts["reply_count"],
                    warning_count,
                    int(saturated),
                    error_message,
                    job_id,
                ),
            )

    def job_rows(self) -> list[sqlite3.Row]:
        with self.connect() as database:
            return database.execute(
                """
                SELECT
                    experiment_id, query_label, query_family, corpus_layer,
                    since_date, until_date, status, attempt_count,
                    fetched_count, search_count, unique_count,
                    duplicate_count, reply_count, warning_count,
                    saturated, started_at, finished_at, error_message
                FROM jobs
                ORDER BY experiment_id, query_family, since_date, query_label
                """
            ).fetchall()

    def saturated_job_labels(self, experiment_id: str | None = None) -> set[str]:
        where = "WHERE saturated = 1"
        parameters: tuple[str, ...] = ()
        if experiment_id:
            where += " AND experiment_id = ?"
            parameters = (experiment_id,)
        with self.connect() as database:
            return {
                row["query_label"]
                for row in database.execute(
                    f"SELECT query_label FROM jobs {where}",
                    parameters,
                ).fetchall()
            }

    def top_conversation_roots(
        self,
        *,
        limit: int,
        minimum_replies: int = 1,
        query_family: str | None = None,
        corpus_layer: str = "core",
    ) -> list[dict[str, Any]]:
        family_filter = ""
        parameters: list[Any] = [minimum_replies, corpus_layer]
        if query_family:
            family_filter = "AND j.query_family = ?"
            parameters.append(query_family)
        parameters.append(limit)
        with self.connect() as database:
            rows = database.execute(
                f"""
                SELECT
                    t.tweet_id,
                    t.conversation_id,
                    t.created_at,
                    MAX(COALESCE(t.reply_count, 0)) AS reply_count
                FROM tweets t
                JOIN captures c ON c.tweet_id = t.tweet_id
                JOIN jobs j ON j.job_id = c.job_id
                WHERE t.tweet_id = t.conversation_id
                  AND c.capture_kind = 'search'
                  AND COALESCE(t.reply_count, 0) >= ?
                  AND j.corpus_layer = ?
                  {family_filter}
                GROUP BY t.tweet_id, t.conversation_id, t.created_at
                ORDER BY reply_count DESC, t.created_at, t.tweet_id
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def audit_metrics(
        self, timezone_name: str = "America/Argentina/Buenos_Aires"
    ) -> dict[str, Any]:
        timezone = ZoneInfo(timezone_name)
        with self.connect() as database:
            totals = database.execute(
                """
                SELECT
                    COUNT(*) AS tweets,
                    COUNT(DISTINCT author_id) AS authors,
                    MIN(created_at) AS date_min_utc,
                    MAX(created_at) AS date_max_utc,
                    SUM(CASE WHEN TRIM(text) = '' THEN 1 ELSE 0 END) AS missing_text,
                    SUM(CASE WHEN author_id IS NULL THEN 1 ELSE 0 END) AS missing_author,
                    SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) AS missing_date,
                    SUM(
                        CASE WHEN like_count IS NULL
                            OR retweet_count IS NULL
                            OR reply_count IS NULL
                        THEN 1 ELSE 0 END
                    ) AS missing_engagement_metrics
                FROM tweets
                """
            ).fetchone()
            relationship_rows = database.execute(
                """
                SELECT relationship_type, COUNT(*) AS count
                FROM relationships
                GROUP BY relationship_type
                """
            ).fetchall()
            capture_rows = database.execute(
                """
                SELECT capture_kind, COUNT(*) AS count
                FROM captures
                GROUP BY capture_kind
                """
            ).fetchall()
            job_rows = database.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            ).fetchall()
            layer_rows = database.execute(
                """
                SELECT j.corpus_layer, c.capture_kind, COUNT(*) AS count
                FROM captures c
                JOIN jobs j ON j.job_id = c.job_id
                GROUP BY j.corpus_layer, c.capture_kind
                """
            ).fetchall()
            user_metadata = database.execute(
                """
                SELECT
                    COUNT(*) AS users,
                    SUM(CASE WHEN TRIM(COALESCE(location, '')) != '' THEN 1 ELSE 0 END)
                        AS with_location,
                    SUM(CASE WHEN created_at IS NOT NULL THEN 1 ELSE 0 END)
                        AS with_created_at,
                    SUM(CASE WHEN followers_count IS NOT NULL THEN 1 ELSE 0 END)
                        AS with_followers
                FROM users
                """
            ).fetchone()
            saturated_jobs = database.execute(
                "SELECT COUNT(*) AS count FROM jobs WHERE saturated = 1"
            ).fetchone()["count"]

        def local_datetime(value: str | None) -> str | None:
            if value is None:
                return None
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(timezone).isoformat()

        relationships = {kind: 0 for kind in ("reply", "quote", "retweet")}
        relationships.update({row["relationship_type"]: row["count"] for row in relationship_rows})
        captures = {kind: 0 for kind in ("search", "reply")}
        captures.update({row["capture_kind"]: row["count"] for row in capture_rows})
        jobs = {status: 0 for status in ("pending", "running", "completed", "failed")}
        jobs.update({row["status"]: row["count"] for row in job_rows})
        captures_by_layer: dict[str, dict[str, int]] = {}
        for row in layer_rows:
            layer = row["corpus_layer"] or "core"
            captures_by_layer.setdefault(layer, {"search": 0, "reply": 0})
            captures_by_layer[layer][row["capture_kind"]] = row["count"]

        return {
            "database": str(self.path),
            "timezone": timezone_name,
            "tweets": totals["tweets"],
            "authors": totals["authors"],
            "date_min_utc": totals["date_min_utc"],
            "date_max_utc": totals["date_max_utc"],
            "date_min_local": local_datetime(totals["date_min_utc"]),
            "date_max_local": local_datetime(totals["date_max_utc"]),
            "missing": {
                "text": totals["missing_text"] or 0,
                "author": totals["missing_author"] or 0,
                "date": totals["missing_date"] or 0,
                "engagement_metrics": totals["missing_engagement_metrics"] or 0,
            },
            "relationships": relationships,
            "captures": captures,
            "captures_by_layer": captures_by_layer,
            "user_metadata": {
                "users": user_metadata["users"],
                "with_declared_location": user_metadata["with_location"] or 0,
                "with_account_creation_date": user_metadata["with_created_at"] or 0,
                "with_follower_count": user_metadata["with_followers"] or 0,
            },
            "saturated_jobs": saturated_jobs,
            "jobs": jobs,
        }

    def merge_databases(self, sources: Iterable[str | Path]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        merge_tables = (
            "users",
            "user_snapshots",
            "tweets",
            "jobs",
            "captures",
            "relationships",
        )
        required_tables = {"users", "tweets", "jobs", "captures", "relationships", "job_events"}

        with self.connect() as database:
            for source in sources:
                source_path = Path(source).resolve()
                if not source_path.exists():
                    raise FileNotFoundError(f"No existe la base de origen: {source_path}")
                if source_path == self.path.resolve():
                    raise ValueError("La base de destino no puede ser también una base de origen")

                database.execute("ATTACH DATABASE ? AS source_db", (str(source_path),))
                try:
                    source_tables = {
                        row["name"]
                        for row in database.execute(
                            "SELECT name FROM source_db.sqlite_master WHERE type = 'table'"
                        ).fetchall()
                    }
                    missing_tables = required_tables - source_tables
                    if missing_tables:
                        missing = ", ".join(sorted(missing_tables))
                        raise ValueError(
                            f"La base {source_path} no tiene el esquema esperado: faltan {missing}"
                        )

                    changes_before = database.total_changes
                    for table in merge_tables:
                        if table not in source_tables:
                            continue
                        main_columns = [
                            row["name"]
                            for row in database.execute(
                                f"PRAGMA main.table_info('{table}')"
                            ).fetchall()
                            if not (table == "captures" and row["name"] == "id")
                        ]
                        source_columns = {
                            row["name"]
                            for row in database.execute(
                                f"PRAGMA source_db.table_info('{table}')"
                            ).fetchall()
                        }
                        columns = [
                            column for column in main_columns if column in source_columns
                        ]
                        column_list = ", ".join(columns)
                        database.execute(
                            f"INSERT OR IGNORE INTO main.{table} ({column_list}) "
                            f"SELECT {column_list} FROM source_db.{table}"
                        )

                    database.execute(
                        """
                        INSERT INTO main.job_events (job_id, occurred_at, level, message)
                        SELECT source.job_id, source.occurred_at, source.level, source.message
                        FROM source_db.job_events AS source
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM main.job_events AS target
                            WHERE target.job_id = source.job_id
                              AND target.occurred_at = source.occurred_at
                              AND target.level = source.level
                              AND target.message = source.message
                        )
                        """
                    )
                    database.commit()
                    reports.append(
                        {
                            "source": str(source_path),
                            "inserted_rows": database.total_changes - changes_before,
                        }
                    )
                finally:
                    database.execute("DETACH DATABASE source_db")

        return reports

    def export_tweets_csv(self, output_path: str | Path) -> int:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as database:
            rows = database.execute(
                """
                SELECT
                    t.*,
                    u.username AS author_username,
                    u.display_name AS author_display_name
                FROM tweets t
                LEFT JOIN users u ON u.user_id = t.author_id
                ORDER BY t.created_at, t.tweet_id
                """
            ).fetchall()

        if not rows:
            destination.write_text("", encoding="utf-8")
            return 0

        with destination.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(dict(row) for row in rows)
        return len(rows)

    def export_annotation_sample(
        self,
        output_path: str | Path,
        *,
        per_layer: int = 100,
        seed: int = 2026,
    ) -> int:
        if per_layer <= 0:
            raise ValueError("per_layer debe ser positivo")
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as database:
            rows = [
                dict(row)
                for row in database.execute(
                    """
                    SELECT
                        t.tweet_id,
                        t.created_at,
                        t.text,
                        t.language,
                        u.username AS author_username,
                        t.like_count,
                        t.retweet_count,
                        t.reply_count,
                        t.quote_count,
                        t.view_count,
                        t.conversation_id,
                        CASE
                            WHEN MAX(CASE WHEN j.corpus_layer = 'core' THEN 1 ELSE 0 END) = 1
                                THEN 'core'
                            ELSE 'thematic'
                        END AS source_layer,
                        GROUP_CONCAT(DISTINCT j.query_family) AS query_families
                    FROM tweets t
                    JOIN captures c ON c.tweet_id = t.tweet_id
                    JOIN jobs j ON j.job_id = c.job_id
                    LEFT JOIN users u ON u.user_id = t.author_id
                    WHERE j.corpus_layer IN ('core', 'thematic')
                    GROUP BY t.tweet_id
                    """
                ).fetchall()
            ]

        selected: list[dict[str, Any]] = []
        for layer in ("core", "thematic"):
            candidates = [row for row in rows if row["source_layer"] == layer]
            candidates.sort(
                key=lambda row: hashlib.sha256(
                    f"{seed}:{row['tweet_id']}".encode()
                ).hexdigest()
            )
            selected.extend(candidates[:per_layer])
        selected.sort(key=lambda row: (row["source_layer"], row["created_at"] or ""))

        fields = (
            "tweet_id",
            "created_at",
            "text",
            "language",
            "author_username",
            "like_count",
            "retweet_count",
            "reply_count",
            "quote_count",
            "view_count",
            "conversation_id",
            "source_layer",
            "query_families",
            "narratives",
            "stance",
            "identity",
            "automation",
            "notes",
        )
        with destination.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for row in selected:
                writer.writerow({field: row.get(field, "") for field in fields})
        return len(selected)

    def export_threads_csv(
        self,
        output_path: str | Path,
        *,
        conversation_id: str | None = None,
    ) -> int:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        where = ""
        parameters: tuple[str, ...] = ()
        if conversation_id:
            where = "WHERE COALESCE(t.conversation_id, t.tweet_id) = ?"
            parameters = (conversation_id,)

        with self.connect() as database:
            records = [
                dict(row)
                for row in database.execute(
                    f"""
                    SELECT
                        COALESCE(t.conversation_id, t.tweet_id) AS conversation_id,
                        t.tweet_id,
                        t.created_at,
                        t.text,
                        t.author_id,
                        u.username AS author_username,
                        u.display_name AS author_display_name,
                        t.like_count,
                        t.retweet_count,
                        t.reply_count,
                        t.reply_to_tweet_id,
                        t.reply_to_user_id,
                        t.reply_to_username,
                        t.quoted_tweet_id,
                        t.quoted_user_id,
                        t.quoted_username,
                        t.quote_count,
                        t.view_count,
                        CASE
                            WHEN EXISTS (
                                SELECT 1 FROM captures AS reply_capture
                                WHERE reply_capture.tweet_id = t.tweet_id
                                  AND reply_capture.capture_kind = 'reply'
                            ) THEN 'reply'
                            ELSE 'search'
                        END AS capture_kind,
                        (
                            SELECT MIN(NULLIF(root_capture.root_tweet_id, ''))
                            FROM captures AS root_capture
                            WHERE root_capture.tweet_id = t.tweet_id
                        ) AS download_root_tweet_id,
                        t.language,
                        t.url
                    FROM tweets AS t
                    LEFT JOIN users AS u ON u.user_id = t.author_id
                    {where}
                    """,
                    parameters,
                ).fetchall()
            ]

        if not records:
            destination.write_text("", encoding="utf-8")
            return 0

        by_id = {str(record["tweet_id"]): record for record in records}
        depths: dict[str, int] = {}

        def depth_for(tweet_id: str, trail: frozenset[str] = frozenset()) -> int:
            if tweet_id in depths:
                return depths[tweet_id]
            record = by_id[tweet_id]
            root_id = str(record["conversation_id"])
            parent_id = record["reply_to_tweet_id"]
            if tweet_id == root_id or not parent_id:
                depth = 0
            elif str(parent_id) in by_id and str(parent_id) not in trail:
                depth = depth_for(str(parent_id), trail | {tweet_id}) + 1
            else:
                depth = 1
            depths[tweet_id] = depth
            return depth

        for record in records:
            tweet_id = str(record["tweet_id"])
            parent_id = record["reply_to_tweet_id"]
            root_id = str(record["conversation_id"])
            record["thread_depth"] = depth_for(tweet_id)
            record["parent_in_dataset"] = int(
                bool(parent_id) and str(parent_id) in by_id
            )
            record["root_in_dataset"] = int(root_id in by_id)

        records.sort(
            key=lambda record: (
                str(record["conversation_id"]),
                int(record["thread_depth"]),
                record["created_at"] or "",
                str(record["tweet_id"]),
            )
        )

        with destination.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=THREAD_EXPORT_FIELDS)
            writer.writeheader()
            writer.writerows(
                {field: record.get(field) for field in THREAD_EXPORT_FIELDS}
                for record in records
            )
        return len(records)


def write_jsonl_records(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
