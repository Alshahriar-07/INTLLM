"""INTLLM command line interface.

Console entry point installed as ``intllm``::

    intllm                 # start the local runtime and open the web UI
    intllm start           # same as above
    intllm serve           # run the headless API server (no browser)
    intllm doctor          # inspect PostgreSQL / Ollama / database readiness
    intllm --version
    intllm --help
"""

from __future__ import annotations

import argparse
import sys

from app import __version__

PROG = "intllm"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="INTLLM - local-first AI runtime with an OpenAI-compatible API.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="print the INTLLM version and exit",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start", help="start the local runtime and open the web UI")
    sub.add_parser("serve", help="run the API server only (no browser window)")
    sub.add_parser(
        "doctor",
        help="check PostgreSQL, Ollama and database readiness, then exit",
    )
    sub.add_parser("version", help="print the INTLLM version and exit")

    return parser


def _cmd_serve() -> int:
    from app.main import run

    run()
    return 0


def _cmd_start() -> int:
    from app.launcher import main as launcher_main

    return launcher_main()


def _cmd_doctor() -> int:
    """Report real readiness. Never fabricates a healthy state."""
    import asyncio

    async def _check() -> int:
        from app.config.settings import get_settings
        from app.db.session import get_database
        from app.services.ollama.process import is_running
        from app.services.system.db_init import inspect as inspect_database

        settings = get_settings()
        problems = 0

        print(f"INTLLM {__version__} - environment doctor")
        print(f"  config: host={settings.intllm_host} port={settings.intllm_port}")

        database = get_database()
        db_ok, db_error = await database.ping()
        if db_ok:
            report = await inspect_database()
            print(f"  postgres: {report.status}")
            if report.detail:
                print(f"            {report.detail}")
            for action in report.actions:
                print(f"            -> {action}")
            if report.status != "running":
                problems += 1
        else:
            print(f"  postgres: unavailable ({db_error})")
            problems += 1

        ollama_ok, ollama_error = await is_running()
        print(f"  ollama:   {'running' if ollama_ok else 'unavailable'}")
        if not ollama_ok and ollama_error:
            print(f"            {ollama_error}")
        if not ollama_ok:
            problems += 1

        await database.dispose()
        if problems:
            print(f"\n{problems} dependency issue(s) detected - see the notes above.")
            return 1
        print("\nAll dependencies are ready.")
        return 0

    return asyncio.run(_check())


_COMMANDS = {
    "start": _cmd_start,
    "serve": _cmd_serve,
    "doctor": _cmd_doctor,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command or "start"
    if command == "version":
        print(f"{PROG} {__version__}")
        return 0

    handler = _COMMANDS.get(command)
    if handler is None:  # pragma: no cover - argparse rejects unknown commands
        parser.print_help()
        return 2
    return handler()


if __name__ == "__main__":
    sys.exit(main())
