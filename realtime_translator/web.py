from __future__ import annotations

import atexit
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .audio import list_audio_devices
from .config import AppConfig
from .worker import EventStore, TranslationWorker


def create_app(config: AppConfig) -> Flask:
    app = Flask(__name__)
    events = EventStore(max_events=config.max_events)
    worker = TranslationWorker(config, events)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/config")
    def get_config():
        return jsonify(config.public_settings())

    @app.get("/api/status")
    def get_status():
        payload = worker.status()
        payload["config"] = config.public_settings()
        return jsonify(payload)

    @app.get("/api/events")
    def get_events():
        after = request.args.get("after", "0")
        try:
            after_id = int(after)
        except ValueError:
            after_id = 0
        return jsonify({"events": events.after(after_id)})

    @app.post("/api/start")
    def start():
        started = worker.start()
        return jsonify({"started": started, "status": worker.status()})

    @app.post("/api/stop")
    def stop():
        worker.stop()
        return jsonify({"stopped": True, "status": worker.status()})

    @app.post("/api/knowledge/refresh")
    def refresh_knowledge():
        count = worker.refresh_knowledge()
        return jsonify({"chunks": count})

    @app.post("/api/suggestions/language")
    def set_suggestions_language():
        payload = request.get_json(silent=True) or {}
        language = str(payload.get("language", "")).strip()
        try:
            selected = worker.set_suggestions_language(language)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"suggestions_language": selected, "status": worker.status()})

    @app.get("/api/devices")
    def devices():
        try:
            return jsonify(list_audio_devices())
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    if config.auto_start:
        worker.start()

    return app


def _write_pid(pid_file: Path) -> None:
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def cleanup() -> None:
        try:
            if pid_file.exists() and pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
                pid_file.unlink()
        except OSError:
            pass

    atexit.register(cleanup)


def run_server(config: AppConfig) -> None:
    _write_pid(config.pid_file)
    app = create_app(config)
    print(f"Open UI: http://{config.app_host}:{config.app_port}")
    app.run(host=config.app_host, port=config.app_port, threaded=True, use_reloader=False)
