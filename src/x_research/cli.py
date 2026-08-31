from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .campaign import (
    generate_experiment,
    generate_thread_experiment,
    load_campaign_config,
    plan_metrics,
    refine_experiment,
    select_queries,
    write_experiment,
)
from .collector import collect_experiment
from .comparison import compare_external_search
from .config import ExperimentConfig, load_config
from .external_audit import audit_external_jsonl
from .parquet import export_parquet_dataset
from .storage import ResearchStore

DEFAULT_CONFIG = Path("config/prueba_minima.json")
DEFAULT_CAMPAIGN = Path("config/campania_mundial_2026.json")
DEFAULT_ACCOUNTS_DB = Path("data/accounts.db")
DEFAULT_DATABASE = Path("data/research.sqlite3")
DEFAULT_RAW_JSONL = Path("data/raw/captures.jsonl")
DEFAULT_CAMPAIGN_RAW = Path("data/raw/campaign")
DEFAULT_PLAN = Path("data/plans/campania_mundial_2026.json")
DEFAULT_THREAD_PLAN = Path("data/plans/hilos_mundial_2026.json")
DEFAULT_CSV = Path("data/exports/tweets.csv")
DEFAULT_THREADS_CSV = Path("data/exports/threads.csv")
DEFAULT_PARQUET = Path("data/parquet/mundial_2026")
DEFAULT_ANNOTATION_CSV = Path("data/exports/muestra_etiquetado.csv")


def _add_runtime_paths(parser: argparse.ArgumentParser, *, campaign: bool = False) -> None:
    parser.add_argument("--accounts-db", type=Path, default=DEFAULT_ACCOUNTS_DB)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--raw-dir" if campaign else "--raw-jsonl",
        type=Path,
        default=DEFAULT_CAMPAIGN_RAW if campaign else DEFAULT_RAW_JSONL,
        help=(
            "Directorio de archivos JSONL separados por trabajo"
            if campaign
            else "Archivo JSONL de capturas"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Volver a ejecutar también los trabajos ya completados",
    )


def _add_partition_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--shard-count",
        type=int,
        default=1,
        help="Cantidad total de computadoras o partes",
    )
    parser.add_argument(
        "--shard-index",
        type=int,
        default=0,
        help="Parte asignada a esta computadora, comenzando en 0",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        help="Ejecutar sólo los primeros N trabajos seleccionados",
    )


def _add_refinement_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--auto-refine",
        action="store_true",
        help="Subdividir y ejecutar automáticamente las ventanas saturadas",
    )
    parser.add_argument(
        "--max-refinement-rounds",
        type=int,
        default=6,
        help="Cantidad máxima de rondas automáticas de subdivisión",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Detener la campaña ante el primer trabajo fallido",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="x-research",
        description="Recolección reproducible de publicaciones públicas de X con twscrape",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-config", help="Validar una configuración pequeña sin conectarse a X"
    )
    validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    validate_campaign = subparsers.add_parser(
        "validate-campaign",
        help="Validar la campaña masiva y mostrar cuántos trabajos generará",
    )
    validate_campaign.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)

    plan_campaign = subparsers.add_parser(
        "plan-campaign",
        help="Generar el plan detallado de trabajos sin conectarse a X",
    )
    plan_campaign.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    plan_campaign.add_argument("--output", type=Path, default=DEFAULT_PLAN)
    _add_partition_options(plan_campaign)

    collect = subparsers.add_parser("collect", help="Ejecutar una configuración pequeña")
    collect.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    _add_runtime_paths(collect)

    collect_campaign = subparsers.add_parser(
        "collect-campaign",
        help="Ejecutar una campaña por ventanas, con reanudación y reparto entre nodos",
    )
    collect_campaign.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    collect_campaign.add_argument("--plan-output", type=Path, default=DEFAULT_PLAN)
    _add_runtime_paths(collect_campaign, campaign=True)
    _add_partition_options(collect_campaign)
    _add_refinement_options(collect_campaign)

    refine = subparsers.add_parser(
        "refine-plan",
        help="Crear un plan más fino sólo para las ventanas que alcanzaron su límite",
    )
    refine.add_argument("--config", type=Path, required=True)
    refine.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    refine.add_argument("--output", type=Path, required=True)

    expand_threads = subparsers.add_parser(
        "expand-threads",
        help="Descargar por conversation_id los hilos más respondidos del corpus principal",
    )
    expand_threads.add_argument("--top", type=int, default=20)
    expand_threads.add_argument("--minimum-replies", type=int, default=10)
    expand_threads.add_argument(
        "--query-family",
        help="Seleccionar raíces halladas por una familia concreta de consultas",
    )
    expand_threads.add_argument(
        "--corpus-layer", default="core", choices=("core", "thematic")
    )
    expand_threads.add_argument("--since", default="2026-06-09")
    expand_threads.add_argument("--until", default="2026-07-22")
    expand_threads.add_argument(
        "--timezone", default="America/Argentina/Buenos_Aires"
    )
    expand_threads.add_argument("--limit-per-thread", type=int, default=1000)
    expand_threads.add_argument("--minimum-window-minutes", type=int, default=10)
    expand_threads.add_argument("--experiment-id", default="mundial_2026_hilos")
    expand_threads.add_argument("--plan-output", type=Path, default=DEFAULT_THREAD_PLAN)
    _add_runtime_paths(expand_threads, campaign=True)
    _add_partition_options(expand_threads)
    _add_refinement_options(expand_threads)

    summary = subparsers.add_parser("summary", help="Mostrar el estado de los trabajos")
    summary.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    audit = subparsers.add_parser(
        "audit", help="Calcular métricas reproducibles de cobertura y completitud"
    )
    audit.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    audit.add_argument(
        "--timezone",
        default="America/Argentina/Buenos_Aires",
        help="Zona horaria para mostrar las fechas mínima y máxima",
    )

    merge = subparsers.add_parser(
        "merge-db", help="Unir bases producidas por varias computadoras sin duplicar tuits"
    )
    merge.add_argument("sources", nargs="+", type=Path, help="Bases SQLite de origen")
    merge.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    export = subparsers.add_parser("export-csv", help="Exportar los tuits únicos a CSV")
    export.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    export.add_argument("--output", type=Path, default=DEFAULT_CSV)

    export_threads = subparsers.add_parser(
        "export-threads-csv",
        help="Exportar tuits agrupados y ordenados por conversación",
    )
    export_threads.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    export_threads.add_argument("--output", type=Path, default=DEFAULT_THREADS_CSV)
    export_threads.add_argument(
        "--conversation-id",
        help="Exportar solamente una conversación",
    )

    export_parquet = subparsers.add_parser(
        "export-parquet",
        help="Exportar un conjunto columnar particionado para análisis masivo",
    )
    export_parquet.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    export_parquet.add_argument("--output", type=Path, default=DEFAULT_PARQUET)

    annotation = subparsers.add_parser(
        "export-annotation-sample",
        help="Crear una muestra reproducible para etiquetado manual",
    )
    annotation.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    annotation.add_argument("--output", type=Path, default=DEFAULT_ANNOTATION_CSV)
    annotation.add_argument("--per-layer", type=int, default=100)
    annotation.add_argument("--seed", type=int, default=2026)

    external_audit = subparsers.add_parser(
        "audit-external-jsonl",
        help="Auditar y limpiar resultados directos e hilos JSONL de otro recolector",
    )
    external_audit.add_argument("--tweets", type=Path, required=True)
    external_audit.add_argument("--threads", type=Path, required=True)
    external_audit.add_argument("--output", type=Path, required=True)
    external_audit.add_argument("--target-date", default="2026-07-19")
    external_audit.add_argument(
        "--timezone", default="America/Argentina/Buenos_Aires"
    )

    compare_external = subparsers.add_parser(
        "compare-external-search",
        help="Comparar por hora e ID una campaña con resultados directos externos",
    )
    compare_external.add_argument("--tweets", type=Path, required=True)
    compare_external.add_argument("--database", type=Path, required=True)
    compare_external.add_argument("--output", type=Path, required=True)
    compare_external.add_argument("--experiment-id", required=True)
    compare_external.add_argument("--target-date", default="2026-07-19")
    compare_external.add_argument(
        "--timezone", default="America/Argentina/Buenos_Aires"
    )

    return parser


def _print_summary(store: ResearchStore) -> None:
    rows = store.job_rows()
    if not rows:
        print("Todavía no hay trabajos registrados.")
        return

    headers = (
        "capa",
        "familia",
        "fechas",
        "estado",
        "búsqueda",
        "únicos",
        "saturado",
        "avisos",
    )
    print(" | ".join(headers))
    print("-" * 120)
    for row in rows:
        values = (
            row["corpus_layer"],
            row["query_family"],
            f"{row['since_date']}..{row['until_date']}",
            row["status"],
            str(row["search_count"]),
            str(row["unique_count"]),
            "sí" if row["saturated"] else "no",
            str(row["warning_count"]),
        )
        print(" | ".join(values))
        if row["error_message"]:
            print(f"  error: {row['error_message']}")


async def _collect_with_refinement(
    experiment: ExperimentConfig,
    *,
    accounts_db: Path,
    database: Path,
    raw_target: Path,
    force: bool,
    auto_refine: bool,
    max_refinement_rounds: int,
    stop_on_error: bool,
) -> list[dict[str, Any]]:
    if max_refinement_rounds < 0:
        raise ValueError("--max-refinement-rounds no puede ser negativo")

    store = ResearchStore(database)
    current = experiment
    rounds: list[dict[str, Any]] = []
    for round_index in range(max_refinement_rounds + 1):
        reports = await collect_experiment(
            current,
            accounts_db=accounts_db,
            database_path=database,
            raw_jsonl=raw_target,
            force=force,
            continue_on_error=not stop_on_error,
        )
        rounds.append(
            {
                "round": round_index,
                "plan": plan_metrics(current),
                "reports": reports,
            }
        )
        if not auto_refine:
            break

        saturated = store.saturated_job_labels(current.experiment_id)
        refined = refine_experiment(current, saturated)
        if not refined.queries:
            break
        current = refined

    return rounds


def _selected_plan(
    experiment: ExperimentConfig,
    args: argparse.Namespace,
) -> ExperimentConfig:
    return select_queries(
        experiment,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
        max_jobs=args.max_jobs,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "validate-config":
            config = load_config(args.config)
            print(f"Configuración válida: {config.experiment_id}")
            print(f"Zona horaria: {config.timezone}")
            for query in config.queries:
                full_query = query.full_query_for(config.timezone)
                print(
                    f"- {query.label} [{query.corpus_layer}/{query.family}]: "
                    f"{full_query} (máximo {query.limit})"
                )
            return 0

        if args.command == "validate-campaign":
            campaign = load_campaign_config(args.campaign)
            experiment = generate_experiment(campaign)
            print(json.dumps(plan_metrics(experiment), ensure_ascii=False, indent=2))
            print(f"Período local: {campaign.since} .. {campaign.until}")
            return 0

        if args.command == "plan-campaign":
            campaign = load_campaign_config(args.campaign)
            experiment = _selected_plan(generate_experiment(campaign), args)
            write_experiment(experiment, args.output, generated_from=str(args.campaign))
            print(json.dumps(plan_metrics(experiment), ensure_ascii=False, indent=2))
            print(f"Plan guardado en {args.output}")
            return 0

        if args.command == "collect":
            config = load_config(args.config)
            reports = asyncio.run(
                collect_experiment(
                    config,
                    accounts_db=args.accounts_db,
                    database_path=args.database,
                    raw_jsonl=args.raw_jsonl,
                    force=args.force,
                )
            )
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 0

        if args.command == "collect-campaign":
            campaign = load_campaign_config(args.campaign)
            experiment = _selected_plan(generate_experiment(campaign), args)
            write_experiment(
                experiment,
                args.plan_output,
                generated_from=str(args.campaign),
            )
            rounds = asyncio.run(
                _collect_with_refinement(
                    experiment,
                    accounts_db=args.accounts_db,
                    database=args.database,
                    raw_target=args.raw_dir,
                    force=args.force,
                    auto_refine=args.auto_refine,
                    max_refinement_rounds=args.max_refinement_rounds,
                    stop_on_error=args.stop_on_error,
                )
            )
            print(json.dumps(rounds, ensure_ascii=False, indent=2))
            return 0

        if args.command == "refine-plan":
            experiment = load_config(args.config)
            saturated = ResearchStore(args.database).saturated_job_labels(
                experiment.experiment_id
            )
            refined = refine_experiment(experiment, saturated)
            if not refined.queries:
                print("No hay ventanas saturadas que puedan subdividirse.")
                return 0
            write_experiment(refined, args.output, generated_from=str(args.config))
            print(json.dumps(plan_metrics(refined), ensure_ascii=False, indent=2))
            print(f"Plan refinado guardado en {args.output}")
            return 0

        if args.command == "expand-threads":
            if args.top <= 0 or args.minimum_replies < 0:
                raise ValueError("--top debe ser positivo y --minimum-replies no negativo")
            store = ResearchStore(args.database)
            roots = store.top_conversation_roots(
                limit=args.top,
                minimum_replies=args.minimum_replies,
                query_family=args.query_family,
                corpus_layer=args.corpus_layer,
            )
            family = f"hilos__{args.query_family or 'todas'}"
            experiment = generate_thread_experiment(
                roots,
                experiment_id=args.experiment_id,
                since=args.since,
                until=args.until,
                timezone=args.timezone,
                limit_per_thread=args.limit_per_thread,
                minimum_window_minutes=args.minimum_window_minutes,
                query_family=family,
            )
            experiment = _selected_plan(experiment, args)
            write_experiment(experiment, args.plan_output, generated_from=str(args.database))
            rounds = asyncio.run(
                _collect_with_refinement(
                    experiment,
                    accounts_db=args.accounts_db,
                    database=args.database,
                    raw_target=args.raw_dir,
                    force=args.force,
                    auto_refine=args.auto_refine,
                    max_refinement_rounds=args.max_refinement_rounds,
                    stop_on_error=args.stop_on_error,
                )
            )
            print(json.dumps(rounds, ensure_ascii=False, indent=2))
            return 0

        if args.command == "summary":
            _print_summary(ResearchStore(args.database))
            return 0

        if args.command == "audit":
            metrics = ResearchStore(args.database).audit_metrics(args.timezone)
            print(json.dumps(metrics, ensure_ascii=False, indent=2))
            return 0

        if args.command == "merge-db":
            reports = ResearchStore(args.database).merge_databases(args.sources)
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 0

        if args.command == "export-csv":
            count = ResearchStore(args.database).export_tweets_csv(args.output)
            print(f"Exportados {count} tuits únicos a {args.output}")
            return 0

        if args.command == "export-threads-csv":
            count = ResearchStore(args.database).export_threads_csv(
                args.output,
                conversation_id=args.conversation_id,
            )
            print(f"Exportadas {count} filas ordenadas por conversación a {args.output}")
            return 0

        if args.command == "export-parquet":
            store = ResearchStore(args.database)
            report = export_parquet_dataset(store.path, args.output)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        if args.command == "export-annotation-sample":
            count = ResearchStore(args.database).export_annotation_sample(
                args.output,
                per_layer=args.per_layer,
                seed=args.seed,
            )
            print(f"Exportadas {count} filas para etiquetado a {args.output}")
            return 0

        if args.command == "audit-external-jsonl":
            report = audit_external_jsonl(
                args.tweets,
                args.threads,
                args.output,
                target_date=args.target_date,
                timezone_name=args.timezone,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        if args.command == "compare-external-search":
            report = compare_external_search(
                args.tweets,
                args.database,
                args.output,
                experiment_id=args.experiment_id,
                target_date=args.target_date,
                timezone_name=args.timezone,
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
