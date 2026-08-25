import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace as Object

import pytest

from x_research.collector import collect_experiment
from x_research.config import ExperimentConfig, QuerySpec


def user(user_id: str, username: str):
    return Object(id_str=user_id, username=username, displayname=username.title())


def tweet(tweet_id: str, *, reply_to: str | None = None, reply_count: int = 0):
    return Object(
        id_str=tweet_id,
        date=datetime(2026, 7, 19, 18, 30, tzinfo=UTC),
        user=user(f"u{tweet_id}", f"usuario{tweet_id}"),
        lang="es",
        rawContent=f"Texto {tweet_id}",
        replyCount=reply_count,
        retweetCount=2,
        likeCount=3,
        quoteCount=0,
        viewCount=4,
        conversationIdStr=reply_to or tweet_id,
        inReplyToTweetIdStr=reply_to,
        inReplyToUser=user(f"u{reply_to}", f"usuario{reply_to}") if reply_to else None,
        inReplyToScreenName=f"usuario{reply_to}" if reply_to else None,
        quotedTweet=None,
        retweetedTweet=None,
        hashtags=["Argentina"],
        url=f"https://x.com/usuario{tweet_id}/status/{tweet_id}",
    )


class FakeAPI:
    async def search(self, query, limit, kv):
        outside = tweet("099")
        outside.date = datetime(2026, 7, 20, 3, 0, tzinfo=UTC)
        yield outside
        yield tweet("100", reply_count=1)
        yield tweet("100", reply_count=1)

    async def tweet_replies(self, tweet_id, limit):
        assert tweet_id == 100
        yield tweet("101", reply_to="100")
        yield tweet("102", reply_to="100")


class EmptyAPI:
    async def search(self, query, limit, kv):
        if False:
            yield None


@pytest.mark.asyncio
async def test_collects_search_and_reply_without_duplicates(tmp_path):
    query = QuerySpec(
        label="general",
        text="Argentina",
        since="2026-07-19",
        until="2026-07-20",
        limit=10,
    )
    config = ExperimentConfig(
        experiment_id="pilot",
        search_product="Latest",
        download_replies=True,
        reply_source_limit=1,
        replies_per_tweet=1,
        reply_delay_seconds=0,
        queries=(query,),
    )
    database_path = tmp_path / "research.sqlite3"

    reports = await collect_experiment(
        config,
        accounts_db=tmp_path / "accounts.db",
        database_path=database_path,
        raw_jsonl=tmp_path / "captures.jsonl",
        api=FakeAPI(),
    )

    assert reports[0]["status"] == "completed"
    assert reports[0]["fetched"] == 3
    assert reports[0]["duplicates"] == 1
    assert reports[0]["filtered_outside_window"] == 1
    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM tweets").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM captures").fetchone()[0] == 2


@pytest.mark.asyncio
async def test_zero_results_marks_job_as_failed(tmp_path):
    query = QuerySpec(
        label="sin_resultados",
        text="consulta",
        since="2026-07-19",
        until="2026-07-20",
        limit=10,
    )
    config = ExperimentConfig(
        experiment_id="empty",
        search_product="Latest",
        download_replies=False,
        reply_source_limit=0,
        replies_per_tweet=0,
        reply_delay_seconds=0,
        queries=(query,),
    )
    database_path = tmp_path / "research.sqlite3"

    with pytest.raises(RuntimeError, match="0 resultados"):
        await collect_experiment(
            config,
            accounts_db=tmp_path / "accounts.db",
            database_path=database_path,
            raw_jsonl=tmp_path / "captures.jsonl",
            api=EmptyAPI(),
        )

    with sqlite3.connect(database_path) as database:
        status, error = database.execute(
            "SELECT status, error_message FROM jobs"
        ).fetchone()
    assert status == "failed"
    assert "0 resultados" in error
