import csv
from dataclasses import replace
from datetime import UTC, datetime

from x_research.config import ExperimentConfig, QuerySpec
from x_research.models import NormalizedTweet
from x_research.storage import ResearchStore


def sample_tweet(tweet_id: str = "200") -> NormalizedTweet:
    return NormalizedTweet(
        tweet_id=tweet_id,
        created_at="2026-07-19T18:30:00+00:00",
        text="Texto",
        language="es",
        url=f"https://x.com/autora/status/{tweet_id}",
        author_id="20",
        author_username="autora",
        author_display_name="Autora",
        like_count=5,
        retweet_count=4,
        reply_count=3,
        quote_count=2,
        view_count=10,
        conversation_id="100",
        reply_to_tweet_id="100",
        reply_to_user_id="10",
        reply_to_username="raiz",
        quoted_tweet_id=None,
        quoted_user_id=None,
        quoted_username=None,
        retweeted_tweet_id=None,
        retweeted_user_id=None,
        retweeted_username=None,
        hashtags=("Argentina",),
        captured_at=datetime.now(UTC).isoformat(),
        author_location="Buenos Aires",
        author_created_at="2015-01-02T00:00:00+00:00",
        author_followers_count=123,
    )


def experiment() -> tuple[ExperimentConfig, QuerySpec]:
    query = QuerySpec(
        label="general",
        text="Argentina",
        since="2026-07-19",
        until="2026-07-20",
        limit=100,
    )
    config = ExperimentConfig(
        experiment_id="pilot",
        search_product="Latest",
        download_replies=True,
        reply_source_limit=5,
        replies_per_tweet=25,
        reply_delay_seconds=0,
        queries=(query,),
    )
    return config, query


def test_deduplicates_capture_and_records_relationship(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    config, query = experiment()
    job_id, should_run = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.0",
    )

    assert should_run
    assert store.record_tweet(job_id, sample_tweet(), capture_kind="search")
    assert not store.record_tweet(job_id, sample_tweet(), capture_kind="search")

    with store.connect() as database:
        assert database.execute("SELECT COUNT(*) FROM tweets").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM user_snapshots").fetchone()[0] == 1
        assert database.execute("SELECT location FROM users").fetchone()[0] == "Buenos Aires"
        relationship = database.execute(
            "SELECT relationship_type, target_tweet_id FROM relationships"
        ).fetchone()

    assert tuple(relationship) == ("reply", "100")


def test_completed_job_is_skipped_unless_forced(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    config, query = experiment()
    job_id, _ = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.0",
    )
    store.finish_job(
        job_id,
        status="completed",
        fetched_count=0,
        duplicate_count=0,
        warning_count=0,
    )

    _, should_run = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.0",
    )
    _, forced = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.0",
        force=True,
    )

    assert not should_run
    assert forced


def test_audit_reports_completeness_dates_and_relationships(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    config, query = experiment()
    job_id, _ = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.0",
    )
    store.record_tweet(job_id, sample_tweet(), capture_kind="search")

    audit = store.audit_metrics()

    assert audit["tweets"] == 1
    assert audit["authors"] == 1
    assert audit["date_min_local"] == "2026-07-19T15:30:00-03:00"
    assert audit["missing"] == {
        "text": 0,
        "author": 0,
        "date": 0,
        "engagement_metrics": 0,
    }
    assert audit["relationships"] == {"reply": 1, "quote": 0, "retweet": 0}
    assert audit["captures"] == {"search": 1, "reply": 0}
    assert audit["jobs"]["running"] == 1


def test_merges_databases_without_duplicating_tweets(tmp_path):
    source_paths = []
    for index in (1, 2):
        source = ResearchStore(tmp_path / f"source-{index}.sqlite3")
        config, query = experiment()
        unique_config = ExperimentConfig(
            experiment_id=f"pilot-{index}",
            search_product=config.search_product,
            download_replies=config.download_replies,
            reply_source_limit=config.reply_source_limit,
            replies_per_tweet=config.replies_per_tweet,
            reply_delay_seconds=config.reply_delay_seconds,
            queries=config.queries,
        )
        job_id, _ = source.prepare_job(
            unique_config,
            query,
            machine=f"node-{index}",
            twscrape_version="0.20.0",
        )
        source.record_tweet(job_id, sample_tweet(), capture_kind="search")
        source.finish_job(
            job_id,
            status="completed",
            fetched_count=1,
            duplicate_count=0,
            warning_count=0,
        )
        source_paths.append(source.path)

    destination = ResearchStore(tmp_path / "merged.sqlite3")
    reports = destination.merge_databases(source_paths)

    assert len(reports) == 2
    with destination.connect() as database:
        assert database.execute("SELECT COUNT(*) FROM tweets").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM captures").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM relationships").fetchone()[0] == 1


def test_exports_threads_grouped_and_ordered(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    config, query = experiment()
    job_id, _ = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.1",
    )
    root = replace(
        sample_tweet("100"),
        created_at="2026-07-19T18:00:00+00:00",
        conversation_id="100",
        reply_to_tweet_id=None,
        reply_to_user_id=None,
        reply_to_username=None,
    )
    direct_reply = replace(
        sample_tweet("101"),
        created_at="2026-07-19T18:10:00+00:00",
        conversation_id="100",
        reply_to_tweet_id="100",
    )
    nested_reply = replace(
        sample_tweet("102"),
        created_at="2026-07-19T18:20:00+00:00",
        conversation_id="100",
        reply_to_tweet_id="101",
    )
    store.record_tweet(job_id, nested_reply, capture_kind="reply", root_tweet_id="100")
    store.record_tweet(job_id, root, capture_kind="search")
    store.record_tweet(job_id, direct_reply, capture_kind="reply", root_tweet_id="100")

    output = tmp_path / "threads.csv"
    count = store.export_threads_csv(output, conversation_id="100")

    with output.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert count == 3
    assert [row["tweet_id"] for row in rows] == ["100", "101", "102"]
    assert [row["thread_depth"] for row in rows] == ["0", "1", "2"]
    assert rows[0]["capture_kind"] == "search"
    assert rows[1]["capture_kind"] == "reply"
    assert rows[2]["reply_to_tweet_id"] == "101"


def test_exports_reproducible_annotation_sample(tmp_path):
    store = ResearchStore(tmp_path / "research.sqlite3")
    config, query = experiment()
    job_id, _ = store.prepare_job(
        config,
        query,
        machine="test",
        twscrape_version="0.20.1",
    )
    for index in range(5):
        store.record_tweet(
            job_id,
            sample_tweet(str(200 + index)),
            capture_kind="search",
        )

    first = tmp_path / "sample-1.csv"
    second = tmp_path / "sample-2.csv"
    assert store.export_annotation_sample(first, per_layer=3, seed=7) == 3
    assert store.export_annotation_sample(second, per_layer=3, seed=7) == 3

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    with first.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert all(row["source_layer"] == "core" for row in rows)
    assert all(row["stance"] == "" for row in rows)
