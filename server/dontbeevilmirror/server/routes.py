import dataclasses

import flask
import flask_limiter
from flask_limiter.util import get_remote_address

from dontbeevilmirror.server import app, gplay, logging
from dontbeevilmirror.server.gplay import AuthenticationOfflineError
from dontbeevilmirror.server.util import TimeoutDueToRateLimit


limiter = flask_limiter.Limiter(get_remote_address, app=app, storage_uri="memory://")
search_limit = limiter.shared_limit("5/second;60/minute;720/hour", scope="search")
details_limit = limiter.shared_limit("3/second;20/minute;120/hour", scope="details")
download_limit = limiter.shared_limit("2/second;10/minute;30/hour", scope="download")


@app.route("/")
def index():
    return flask.redirect(
        "https://github.com/radian-software/dontbeevilmirror", code=301
    )


@app.route("/api/v0/search", methods=["POST"])
@search_limit
def search():
    query = flask.request.args.get("query")
    if not query:
        return "No query provided", 422
    try:
        resp = gplay.search(query)
    except TimeoutDueToRateLimit:
        return "Too many requests", 503
    return flask.jsonify([dataclasses.asdict(app) for app in resp])


@app.route("/api/v0/details", methods=["POST"])
@details_limit
def details():
    app_ids = flask.request.args.getlist("app")
    if not app_ids:
        return "No app ID(s) provided", 422
    try:
        resp = gplay.details(*app_ids)
    except TimeoutDueToRateLimit:
        return "Too many requests", 503
    except AuthenticationOfflineError:
        return "Server authentication currently offline", 503
    except Exception as e:
        gplay.auth_needs_recheck = True
        logging.error(
            "Got error on details request",
            extra={
                "error": repr(e),
            },
        )
        return "Got unexpected error", 500
    return flask.jsonify(
        {app_id: dataclasses.asdict(app) for app_id, app in resp.items()}
    )
