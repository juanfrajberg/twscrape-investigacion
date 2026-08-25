import json

import pytest

from x_research.config import load_config


def test_loads_valid_config(tmp_path):
    path = tmp_path / "experiment.json"
    path.write_text(
        json.dumps(
            {
                "experiment_id": "pilot",
                "queries": [
                    {
                        "label": "general",
                        "text": "Argentina lang:es",
                        "since": "2026-07-19",
                        "until": "2026-07-20",
                        "limit": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.experiment_id == "pilot"
    assert config.timezone == "America/Argentina/Buenos_Aires"
    assert config.queries[0].full_query_for(config.timezone) == (
        "Argentina lang:es since_time:1784430000 until_time:1784516400"
    )
    assert config.search_product == "Latest"


def test_rejects_reversed_dates(tmp_path):
    path = tmp_path / "experiment.json"
    path.write_text(
        json.dumps(
            {
                "experiment_id": "pilot",
                "queries": [
                    {
                        "label": "bad",
                        "text": "Argentina",
                        "since": "2026-07-20",
                        "until": "2026-07-19",
                        "limit": 10,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="since"):
        load_config(path)


def test_supports_hourly_partitions(tmp_path):
    path = tmp_path / "hourly.json"
    path.write_text(
        json.dumps(
            {
                "experiment_id": "pilot-hourly",
                "timezone": "America/Argentina/Buenos_Aires",
                "queries": [
                    {
                        "label": "midnight_to_six",
                        "text": "Argentina",
                        "since": "2026-07-19T00:00:00",
                        "until": "2026-07-19T06:00:00",
                        "limit": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.queries[0].epoch_bounds(config.timezone) == (
        1784430000,
        1784451600,
    )
    assert config.queries[0].full_query_for(config.timezone) == (
        "Argentina since_time:1784430000 until_time:1784451600"
    )


def test_rejects_datetime_with_embedded_timezone(tmp_path):
    path = tmp_path / "timezone.json"
    path.write_text(
        json.dumps(
            {
                "experiment_id": "pilot-timezone",
                "queries": [
                    {
                        "label": "bad-timezone",
                        "text": "Argentina",
                        "since": "2026-07-19T00:00:00-03:00",
                        "until": "2026-07-19T06:00:00-03:00",
                        "limit": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sin zona horaria"):
        load_config(path)
