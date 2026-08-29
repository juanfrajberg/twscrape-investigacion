from x_research.campaign import (
    CampaignConfig,
    CampaignQuery,
    WindowOverride,
    generate_experiment,
    generate_thread_experiment,
    refine_experiment,
    select_queries,
)
from x_research.config import QuerySpec


def campaign() -> CampaignConfig:
    return CampaignConfig(
        campaign_id="mundial",
        description="Prueba",
        timezone="America/Argentina/Buenos_Aires",
        since="2026-07-19T00:00:00",
        until="2026-07-19T04:00:00",
        search_product="Latest",
        default_window_minutes=120,
        limit_per_job=100,
        minimum_window_minutes=10,
        queries=(
            CampaignQuery(
                label="general",
                text="Argentina Mundial",
                corpus_layer="core",
                window_minutes=120,
                limit=100,
                minimum_results=0,
                minimum_window_minutes=10,
            ),
        ),
        overrides=(
            WindowOverride(
                label="pico",
                since="2026-07-19T01:00:00",
                until="2026-07-19T03:00:00",
                window_minutes=30,
                query_families=("general",),
            ),
        ),
    )


def test_generates_windows_and_respects_peak_override():
    experiment = generate_experiment(campaign())

    assert [(query.since, query.until) for query in experiment.queries] == [
        ("2026-07-19T00:00:00", "2026-07-19T01:00:00"),
        ("2026-07-19T01:00:00", "2026-07-19T01:30:00"),
        ("2026-07-19T01:30:00", "2026-07-19T02:00:00"),
        ("2026-07-19T02:00:00", "2026-07-19T02:30:00"),
        ("2026-07-19T02:30:00", "2026-07-19T03:00:00"),
        ("2026-07-19T03:00:00", "2026-07-19T04:00:00"),
    ]
    assert all(query.query_family == "general" for query in experiment.queries)


def test_refines_only_saturated_windows():
    query = QuerySpec(
        label="general__window",
        text="Argentina",
        since="2026-07-19T00:00:00",
        until="2026-07-19T01:00:00",
        limit=100,
        minimum_results=0,
        query_family="general",
        minimum_window_minutes=10,
    )
    experiment = generate_experiment(campaign())
    experiment = experiment.__class__(
        experiment_id="manual",
        search_product=experiment.search_product,
        download_replies=False,
        reply_source_limit=0,
        replies_per_tweet=0,
        reply_delay_seconds=0,
        queries=(query,),
        timezone=experiment.timezone,
    )

    refined = refine_experiment(experiment, {query.label})

    assert len(refined.queries) == 2
    assert refined.queries[0].since == "2026-07-19T00:00:00"
    assert refined.queries[0].until == "2026-07-19T00:30:00"
    assert refined.queries[1].since == "2026-07-19T00:30:00"
    assert refined.queries[1].until == "2026-07-19T01:00:00"


def test_selects_deterministic_shard():
    experiment = generate_experiment(campaign())

    selected = select_queries(
        experiment,
        shard_count=2,
        shard_index=1,
        max_jobs=2,
    )

    assert selected.queries == experiment.queries[1::2][:2]


def test_generates_thread_queries_with_conversation_id():
    experiment = generate_thread_experiment(
        [{"tweet_id": "100", "conversation_id": "100", "reply_count": 50}],
        experiment_id="threads",
        since="2026-06-09",
        until="2026-07-22",
        timezone="America/Argentina/Buenos_Aires",
        limit_per_thread=1000,
        minimum_window_minutes=10,
        query_family="hilos_general",
    )

    query = experiment.queries[0]
    assert query.text == "conversation_id:100"
    assert query.conversation_id == "100"
    assert query.corpus_layer == "thread"


def test_refined_thread_labels_remain_unique_between_conversations():
    experiment = generate_thread_experiment(
        [
            {"tweet_id": "100", "conversation_id": "100"},
            {"tweet_id": "200", "conversation_id": "200"},
        ],
        experiment_id="threads",
        since="2026-07-19T00:00:00",
        until="2026-07-19T01:00:00",
        timezone="America/Argentina/Buenos_Aires",
        limit_per_thread=100,
        minimum_window_minutes=10,
        query_family="hilos",
    )

    refined = refine_experiment(
        experiment,
        {query.label for query in experiment.queries},
    )

    labels = [query.label for query in refined.queries]
    assert len(labels) == len(set(labels))
    assert any("conversation_100" in label for label in labels)
    assert any("conversation_200" in label for label in labels)
