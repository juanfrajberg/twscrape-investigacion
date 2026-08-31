import json

from x_research.comparison import compare_external_search
from x_research.storage import ResearchStore


def test_compares_external_and_local_direct_ids(tmp_path):
    external = tmp_path / "tweets.jsonl"
    external.write_text(
        "\n".join(
            [
                json.dumps({"tweet_id": "100", "date": "2026-07-19T15:00:00Z"}),
                json.dumps({"tweet_id": "200", "date": "2026-07-20T15:00:00Z"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    database = tmp_path / "research.sqlite3"
    ResearchStore(database)
    with ResearchStore(database).connect() as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                job_id, experiment_id, query_label, query_family, corpus_layer,
                query_text, since_date, until_date, full_query, target_limit,
                search_product, status, search_count, saturated
            ) VALUES ('job', 'comparison', 'q', 'argentina', 'core', 'Argentina',
                      '2026-07-19', '2026-07-20', 'Argentina', 1000,
                      'Latest', 'completed', 2, 0)
            """
        )
        for tweet_id, created_at in (
            ("100", "2026-07-19T15:00:00+00:00"),
            ("300", "2026-07-19T16:00:00+00:00"),
        ):
            connection.execute(
                """
                INSERT INTO tweets (
                    tweet_id, created_at, text, hashtags_json, cashtags_json,
                    mentioned_user_ids_json, mentioned_usernames_json, links_json,
                    media_json, captured_at, source_provider
                ) VALUES (?, ?, '', '[]', '[]', '[]', '[]', '[]', '[]', ?, 'test')
                """,
                (tweet_id, created_at, created_at),
            )
            connection.execute(
                """
                INSERT INTO captures (job_id, tweet_id, capture_kind, root_tweet_id, captured_at)
                VALUES ('job', ?, 'search', '', ?)
                """,
                (tweet_id, created_at),
            )

    report = compare_external_search(
        external,
        database,
        tmp_path / "comparison",
        experiment_id="comparison",
    )

    assert report["external_direct_target_day"] == 1
    assert report["local_direct_target_day"] == 2
    assert report["overlap_target_day"] == 1
    assert report["completed_jobs"] == 1
