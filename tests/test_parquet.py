from datetime import UTC, datetime

import pytest

from x_research.config import ExperimentConfig, QuerySpec
from x_research.models import NormalizedTweet
from x_research.parquet import export_parquet_dataset
from x_research.storage import ResearchStore

pq = pytest.importorskip("pyarrow.parquet")


def test_exports_partitioned_parquet_dataset(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    query = QuerySpec(
        label="general",
        text="Argentina",
        since="2026-07-19",
        until="2026-07-20",
        limit=10,
        query_family="general",
        corpus_layer="core",
    )
    experiment = ExperimentConfig(
        experiment_id="pilot",
        search_product="Latest",
        download_replies=False,
        reply_source_limit=0,
        replies_per_tweet=0,
        reply_delay_seconds=0,
        queries=(query,),
    )
    job_id, _ = store.prepare_job(
        experiment,
        query,
        machine="test",
        twscrape_version="0.20.1",
    )
    store.record_tweet(
        job_id,
        NormalizedTweet(
            tweet_id="100",
            created_at="2026-07-19T18:00:00+00:00",
            text="Argentina",
            language="es",
            url="https://x.com/a/status/100",
            author_id="10",
            author_username="a",
            author_display_name="A",
            like_count=1,
            retweet_count=2,
            reply_count=3,
            quote_count=4,
            view_count=5,
            conversation_id="100",
            reply_to_tweet_id=None,
            reply_to_user_id=None,
            reply_to_username=None,
            quoted_tweet_id=None,
            quoted_user_id=None,
            quoted_username=None,
            retweeted_tweet_id=None,
            retweeted_user_id=None,
            retweeted_username=None,
            hashtags=("Argentina",),
            captured_at=datetime.now(UTC).isoformat(),
        ),
        capture_kind="search",
    )

    output = tmp_path / "parquet"
    report = export_parquet_dataset(store.path, output)

    assert report["tweets"] == 1
    assert report["captures"] == 1
    tweets = pq.read_table(
        output / "tweets" / "date=2026-07-19" / "part-00000.parquet"
    )
    captures = pq.read_table(
        output
        / "captures"
        / "layer=core"
        / "family=general"
        / "part-00000.parquet"
    )
    assert tweets.num_rows == 1
    assert captures.num_rows == 1
