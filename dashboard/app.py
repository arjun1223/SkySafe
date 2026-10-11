"""Run from repository root: python -m dashboard.app"""
import atexit
import argparse
import logging
from pathlib import Path
from urllib.parse import urlsplit
import serial
from flask import Flask, jsonify, request, send_file, abort, render_template
from plotly.offline import get_plotlyjs
from .data_logging import DATA_DIR
from .engine import Engine
from .serial_reader import SerialReader


def create_app(engine=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8192
    engine = engine or Engine()
    app.extensions["skysafe"] = engine

    @app.before_request
    def local_requests_only():
        # Prevent websites from commanding a loopback serial device through this API.
        if request.host.split(":")[0] not in {"127.0.0.1", "localhost", "[::1]"}:
            abort(403)
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            abort(403)
        if request.method == "POST" and not request.is_json:
            abort(415)

    @app.errorhandler(ValueError)
    def bad_input(exc):
        return jsonify(ok=False, message=str(exc)), 400

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/static/vendor/plotly.min.js")
    def plotly_asset():
        # Served from the installed Python package: no internet/CDN during judging.
        return app.response_class(get_plotlyjs(), mimetype="application/javascript",
                                  headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/api/state")
    def state():
        return jsonify(engine.snapshot(request.args.get("after", default=0, type=int)))

    @app.get("/api/ports")
    def ports():
        return jsonify(ports=SerialReader.ports())

    def body():
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data

    @app.post("/api/source")
    def source():
        data = body()
        try:
            engine.switch_source(data.get("source"), data.get("port"))
        except (OSError, serial.SerialException) as exc:
            raise ValueError(str(exc))
        return jsonify(ok=True, message="Data source changed.")

    @app.post("/api/command")
    def command():
        data = body()
        if not isinstance(data.get("command"), str):
            raise ValueError("Command must be a string.")
        return jsonify(engine.command(data["command"], data.get("force")))

    @app.post("/api/demo")
    def demo():
        data = body()
        if set(data) - {"mode", "auto_force", "force", "prepare", "ultrasonic"}:
            raise ValueError("Unknown demo control.")
        if "prepare" in data and not isinstance(data["prepare"], bool):
            raise ValueError("Prepare must be true or false.")
        return jsonify(engine.demo_control(**data))

    @app.post('/api/test')
    def demo_test():
        data = body()
        if set(data)-{'action','target'}:
            raise ValueError('Unknown demo test option.')
        return jsonify(engine.test_control(data.get('action'), data.get('target')))

    @app.post("/api/runs/start")
    def start_run():
        return jsonify(engine.start_run(body().get("name", "wing-test")))

    @app.post("/api/runs/stop")
    def stop_run():
        body()
        return jsonify(engine.stop_run())

    @app.get("/api/runs")
    def runs():
        with engine.lock:
            return jsonify(files=engine.logger.files())

    @app.get("/api/runs/<name>")
    def download(name):
        if Path(name).name != name or not name.endswith(".csv"):
            abort(404)
        path = engine.logger.directory / name
        if not path.is_file():
            abort(404)
        return send_file(path, as_attachment=True)

    return app


def main():
    parser = argparse.ArgumentParser(description="SkySafe local benchtop dashboard")
    parser.add_argument("--port", type=int, default=5050, help="Local web port")
    parser.add_argument("--serial", help="ESP32 USB serial port (otherwise laptop demo)")
    args = parser.parse_args()
    engine = Engine()
    if args.serial:
        try:
            engine.switch_source("serial", args.serial)
        except (OSError, serial.SerialException) as exc:
            # Keep hardware mode visible while the unplugged board reconnects.
            engine.source = "serial"
            engine.serial_port = args.serial
            engine.connection_error = str(exc)
    engine.start()
    atexit.register(engine.close)
    print(f"SkySafe ready: http://127.0.0.1:{args.port}", flush=True)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    create_app(engine).run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
