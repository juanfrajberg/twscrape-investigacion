from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .collector import collect_experiment
from .config import load_config
from .storage import ResearchStore

DEFAULT_CONFIG = Path("config/prueba_minima.json")
DEFAULT_ACCOUNTS_DB = Path("data/accounts.db")
DEFAULT_DATABASE = Path("data/research.sqlite3")
DEFAULT_RAW_JSONL = Path("data/raw/captures.jsonl")
DEFAULT_CSV = Path("data/exports/tweets.csv")
DEFAULT_THREADS_CSV = Path("data/exports/threads.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="x-research",
        description="Recolección reproducible de publicaciones públicas de X con twscrape",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-config", help="Validar la configuración sin conectarse a X"
    )
    validate.add_argument("--config", type=Path, default=DEFAULT_CONFIG)

    collect = subparsers.add_parser("collect", help="Ejecutar el experimento")
    collect.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    collect.add_argument("--accounts-db", type=Path, default=DEFAULT_ACCOUNTS_DB)
    collect.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    collect.add_argument("--raw-jsonl", type=Path, default=DEFAULT_RAW_JSONL)
    collect.add_argument(
        "--force",
        action="store_true",
        help="Volver a ejecutar también los trabajos ya completados",
    )

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

    return parser


def _print_summary(store: ResearchStore) -> None:
    rows = store.job_rows()
    if not rows:
        print("Todavía no hay trabajos registrados.")
        return

    headers = ("consulta", "fechas", "estado", "obtenidos", "únicos", "respuestas", "avisos")
    print(" | ".join(headers))
    print("-" * 100)
    for row in rows:
        values = (
            row["query_label"],
            f"{row['since_date']}..{row['until_date']}",
            row["status"],
            str(row["fetched_count"]),
            str(row["unique_count"]),
            str(row["reply_count"]),
            str(row["warning_count"]),
        )
        print(" | ".join(values))
        if row["error_message"]:
            print(f"  error: {row['error_message']}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate-config":
        config = load_config(args.config)
        print(f"Configuración válida: {config.experiment_id}")
        print(f"Zona horaria: {config.timezone}")
        for query in config.queries:
            full_query = query.full_query_for(config.timezone)
            print(f"- {query.label}: {full_query} (máximo {query.limit})")
        return 0

    if args.command == "collect":
        config = load_config(args.config)
        try:
            reports = asyncio.run(
                collect_experiment(
                    config,
                    accounts_db=args.accounts_db,
                    database_path=args.database,
                    raw_jsonl=args.raw_jsonl,
                    force=args.force,
                )
            )
        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(json.dumps(reports, ensure_ascii=False, indent=2))
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

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
