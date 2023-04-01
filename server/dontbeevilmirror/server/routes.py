import dataclasses

import flask

from dontbeevilmirror.server import app, gplay
from dontbeevilmirror.server.util import TimeoutDueToRateLimit


@app.route("/")
def index():
    return flask.redirect(
        "https://github.com/radian-software/dontbeevilmirror", code=301
    )


@app.route("/api/v0/search", methods=["POST"])
def search():
    query = flask.request.args.get("query")
    if not query:
        return "No query provided", 422
    try:
        resp = gplay.search(query)
    except TimeoutDueToRateLimit:
        return "Too many requests", 503
    return flask.jsonify([dataclasses.asdict(app) for app in resp])
