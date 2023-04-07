import dataclasses

import flask
import flask_limiter
from flask_limiter.util import get_remote_address

from dontbeevilmirror.api import MinimalDetailApp
from dontbeevilmirror.server import app, copier_instance, db, gplay, logging
from dontbeevilmirror.server.copier import NotAuthenticatedError, QueueFullError
from dontbeevilmirror.server.gplay import AuthenticationOfflineError
from dontbeevilmirror.server.util import TimeoutDueToRateLimit


limiter = flask_limiter.Limiter(get_remote_address, app=app, storage_uri="memory://")
search_limit = limiter.shared_limit("5/second;60/minute;720/hour", scope="search")
details_limit = limiter.shared_limit("3/second;20/minute;120/hour", scope="details")
download_limit = limiter.shared_limit("5/second;360/minute;3600/hour", scope="download")
acquire_limit = limiter.shared_limit("2/second;10/minute;30/hour", scope="acquire")
acquire_status_limit = limiter.shared_limit(
    "2/second;60/minute;120/hour", scope="acquire_status"
)


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
        resp = gplay.get_details(*app_ids)
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


@app.route("/api/v0/download", methods=["POST"])
@download_limit
def download():
    try:
        apps = [MinimalDetailApp.fromdict(obj) for obj in list(flask.request.json)]
    except Exception:
        return "Bad app info format provided", 422
    if not apps:
        return "Empty apps list provided", 422
    if len(apps) > len(set(apps)):
        return "Duplicate app ID(s) provided", 422
    try:
        with db.cursor() as curs:
            resp = db.get_download_links(curs, *apps)
    except Exception as e:
        logging.error(
            "Got error on download request",
            extra={
                "error": repr(e),
            },
        )
        return "Got unexpected error", 500
    return flask.jsonify(
        {
            app_id: url
            and dataclasses.asdict(url.with_full_url(copier_instance.url_prefix))
            for app_id, url in resp.items()
        }
    )


@app.route("/api/v0/acquire", methods=["POST"])
@acquire_limit
def acquire():
    app_id = flask.request.args.get("app_id")
    version_code = flask.request.args.get("version_code")
    offer_type = flask.request.args.get("offer_type")
    if not (app_id and version_code and offer_type):
        return "Required parameters not provided", 422
    try:
        copier_instance.request_app(
            MinimalDetailApp(
                id=app_id, version_code=version_code, offer_type=offer_type
            )
        )
    except QueueFullError:
        return "Too many requests", 503
    except NotAuthenticatedError:
        return "Server authentication currently offline", 503
    except Exception as e:
        logging.error(
            "Got error on acquire request",
            extra={
                "error": repr(e),
            },
        )
        return "Got unexpected error", 500
    return "", 204


@app.route("/api/v0/acquire/status", methods=["POST"])
@acquire_status_limit
def acquire_status():
    app_id = flask.request.args.get("app_id")
    version_code = flask.request.args.get("version_code")
    offer_type = flask.request.args.get("offer_type")
    if not (app_id and version_code and offer_type):
        return "Required parameters not provided", 422
    try:
        status = copier_instance.get_app_status(
            MinimalDetailApp(
                id=app_id, version_code=version_code, offer_type=offer_type
            )
        )
        return flask.jsonify(
            {
                "status": status,
            }
        )
    except Exception as e:
        logging.error(
            "Got error on acquire status request",
            extra={
                "error": repr(e),
            },
        )
        return "Got unexpected error", 500
