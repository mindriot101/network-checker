from flask import Flask, render_template, jsonify  # type: ignore
import os


BASE_DIR = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


app = Flask("netcheck", template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def data():
    return jsonify(results={})


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--db", required=True, help="Database file to load from")
    parser.add_argument("--host", required=False, default="127.0.0.1")
    parser.add_argument("--port", required=False, default=5000, type=int)
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()

    app.run(host=args.host, debug=args.debug, port=args.port)
