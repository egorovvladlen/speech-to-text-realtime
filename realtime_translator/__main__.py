from __future__ import annotations

import argparse
import json

from .config import AppConfig


def _check_env(config: AppConfig) -> None:
    settings = config.public_settings()
    print(json.dumps(settings, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Realtime speaker audio translator")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Start local web UI")
    subparsers.add_parser("devices", help="List speaker and loopback audio devices")
    subparsers.add_parser("check-env", help="Print effective .env settings")
    args = parser.parse_args()

    config = AppConfig.from_env()

    if args.command == "devices":
        from .audio import list_audio_devices

        print(json.dumps(list_audio_devices(), ensure_ascii=False, indent=2))
        return
    if args.command == "check-env":
        _check_env(config)
        return

    from .web import run_server

    run_server(config)


if __name__ == "__main__":
    main()
