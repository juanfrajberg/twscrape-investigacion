import csv
import json

from x_research.external_audit import audit_external_jsonl


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _tweet(tweet_id, conversation_id, date, *, parent=None, text="Argentina"):
    return {
        "tweet_id": tweet_id,
        "username": f"user_{tweet_id}",
        "displayname": "Usuario",
        "date": date,
        "text": text,
        "likes": 1,
        "retweets": 0,
        "replies": 0,
        "quotes": 0,
        "views": 10,
        "conversation_id": conversation_id,
        "in_reply_to": parent,
        "in_reply_to_user": None,
        "mentioned_users": [],
        "hashtags": [],
        "lang": "es",
        "url": f"https://x.com/user/status/{tweet_id}",
    }


def test_audits_search_threads_roots_and_windows(tmp_path):
    tweets = tmp_path / "tweets.jsonl"
    threads = tmp_path / "threads.jsonl"
    output = tmp_path / "audit"
    direct_root = _tweet("100", "100", "2026-07-19T15:00:00+00:00")
    direct_reply = _tweet(
        "101", "100", "2026-07-19T15:10:00+00:00", parent="100"
    )
    missing_root_reply = _tweet(
        "201",
        "200",
        "2026-07-20T04:00:00+00:00",
        parent="200",
        text="respuesta sin palabra clave",
    )
    _write_jsonl(tweets, [direct_root, direct_reply])
    _write_jsonl(
        threads,
        [
            {"conversation_id": "100", "tweets": [direct_root, direct_reply]},
            {"conversation_id": "200", "tweets": [missing_root_reply]},
        ],
    )

    report = audit_external_jsonl(tweets, threads, output)

    assert report["volume"]["direct_unique"] == 2
    assert report["volume"]["thread_unique"] == 3
    assert report["volume"]["union_unique"] == 3
    assert report["roots_and_links"]["root_present"] == 1
    assert report["roots_and_links"]["root_missing"] == 1
    assert report["roots_and_links"]["missing_parent_tweets"] == 1
    assert report["temporal"]["thread_unique_outside_research_day_art"] == 1

    with (output / "tweets_clean.csv").open(encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 3
    missing = next(row for row in rows if row["tweet_id"] == "201")
    assert missing["root_status"] == "root_missing"
    assert missing["parent_status"] == "parent_missing"
