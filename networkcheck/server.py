from flask import Flask, render_template, jsonify  # type: ignore
import os
import logging
from .db import Database


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("networkcheck-server")


BASE_DIR = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get("HTTP_X_SCRIPT_NAME", "")
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ["PATH_INFO"]
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name) :]

        scheme = environ.get("HTTP_X_SCHEME", "")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.app(environ, start_response)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--db", required=True, help="Database file to load from")
    parser.add_argument("--host", required=False, default="127.0.0.1")
    parser.add_argument("--port", required=False, default=5000, type=int)
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()

    app = Flask("netcheck", template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
    app.wsgi_app = ReverseProxied(app.wsgi_app)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/responsetimes")
    def response_times():
        with Database(args.db, clear=False, create=False) as db:
            return jsonify(results=db.response_times())

    @app.route("/api/gaps")
    def gaps():
        with Database(args.db, clear=False, create=False) as db:
            return jsonify(results=db.gaps())

    app.run(host=args.host, debug=args.debug, port=args.port)
