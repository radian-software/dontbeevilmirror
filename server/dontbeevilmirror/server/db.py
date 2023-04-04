from contextlib import contextmanager
import dataclasses
import json
import os

import psycopg2.extras
import psycopg2.pool

from dontbeevilmirror.api import (
    Credentials,
    DetailApp,
    DownloadLink,
    MinimalDetailApp,
    PathOnlyDownloadLink,
)
from dontbeevilmirror.server import logging
from dontbeevilmirror.server.util import now

database_url = os.environ["DATABASE_URL"]
if "${POSTGRES_PASSWORD}" in database_url:
    database_url = database_url.replace(
        "${POSTGRES_PASSWORD}", os.environ["POSTGRES_PASSWORD"]
    )

pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=0,
    maxconn=5,
    dsn=database_url,
    cursor_factory=psycopg2.extras.DictCursor,
)


@contextmanager
def connection():
    conn = pool.getconn()
    try:
        with conn:
            yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def cursor():
    with connection() as conn:
        with conn.cursor() as curs:
            yield curs


def set_credentials(curs, creds: Credentials):
    curs.execute(
        "INSERT INTO google_play_authentication (create_ts, format_version, auth_data) VALUES (%(create_ts)s, %(format_version)s, %(auth_data)s)",
        {
            "create_ts": now(),
            "format_version": 1,
            "auth_data": json.dumps(dataclasses.asdict(creds)),
        },
    )


def get_credentials(curs) -> Credentials | None:
    curs.execute(
        "SELECT auth_data FROM google_play_authentication WHERE format_version = 1 ORDER BY create_ts DESC LIMIT 1"
    )
    if obj := curs.fetchone():
        return Credentials.fromdict(obj["auth_data"])


def get_details(curs, *app_ids: str) -> dict[str, DetailApp | None]:
    curs.execute(
        "SELECT app.id, app.validate_ts, app.version_code, app.version_string, app.offer_type, app.free_app FROM (SELECT id, max(create_ts) AS latest FROM app_detail WHERE id IN %(app_ids)s GROUP BY id) AS time INNER JOIN app_detail AS app ON app.id = time.id AND app.create_ts = time.latest",
        {
            "app_ids": app_ids,
        },
    )
    res = {}
    for obj in curs.fetchall():
        res[obj["id"]] = DetailApp(
            id=obj["id"],
            version_code=obj["version_code"],
            version_string=obj["version_string"],
            offer_type=obj["offer_type"],
            free=obj["free_app"],
            created=obj["validate_ts"],
        )
    for app_id in app_ids:
        res.setdefault(app_id, None)
    return res


def set_details(curs, *apps: DetailApp, existing_apps=None) -> None:
    if not existing_apps:
        existing_apps = get_details(curs, *[app.id for app in apps])
    matching_apps = [app for app in apps if existing_apps.get(app.id) == app]
    nonmatching_apps = [app for app in apps if existing_apps.get(app.id) != app]
    logging.trace(
        "Updating apps in database",
        extra={
            "apps_updated": list(sorted(app.id for app in matching_apps)),
            "apps_inserted": list(sorted(app.id for app in nonmatching_apps)),
        },
    )
    curs.executemany(
        "UPDATE app_detail SET validate_ts = %(validate_ts)s WHERE id = %(id)s AND version_code = %(version_code)s AND version_string = %(version_string)s AND offer_type = %(offer_type)s AND free_app = %(free_app)s",
        [
            {
                "validate_ts": app.created,
                "id": app.id,
                "version_code": app.version_code,
                "version_string": app.version_string,
                "offer_type": app.offer_type,
                "free_app": app.free,
            }
            for app in matching_apps
        ],
    )
    psycopg2.extras.execute_values(
        curs,
        "INSERT INTO app_detail (create_ts, validate_ts, id, version_code, version_string, offer_type, free_app) VALUES %s",
        [
            {
                "create_ts": app.created,
                "validate_ts": app.created,
                "id": app.id,
                "version_code": app.version_code,
                "version_string": app.version_string,
                "offer_type": app.offer_type,
                "free_app": app.free,
            }
            for app in nonmatching_apps
        ],
        "(%(create_ts)s, %(validate_ts)s, %(id)s, %(version_code)s, %(version_string)s, %(offer_type)s, %(free_app)s)",
    )


def get_download_links(
    curs, *apps: MinimalDetailApp
) -> dict[str, PathOnlyDownloadLink | None]:
    curs.execute(
        "SELECT app_detail.id, apk.create_ts, apk.object_gz_path, apk.object_gz_bytes, apk.object_bytes, apk.object_sha256_digest FROM apk INNER JOIN app_detail ON apk.app_detail_id = app_detail.id WHERE "
        + " OR ".join(
            curs.mogrify(
                "app_detail.id = %(app_id)s AND app_detail.version_code = %(version_code)s AND app_detail.offer_type = %(offer_type)s",
                {
                    "app_id": app.id,
                    "version_code": app.version_code,
                    "offer_type": app.offer_type,
                },
            )
            for app in apps
        )
    )
    res = {}
    for obj in curs.fetchall():
        obj[obj["id"]] = PathOnlyDownloadLink(
            apk_gz_url=obj["object_gz_path"],
            apk_gz_bytes=obj["object_gz_bytes"],
            apk_bytes=obj["object_bytes"],
            sha256_digest=obj["object_sha256_digest"],
            created=obj["created_ts"],
        )
    for app in apps:
        res.setdefault(app.id, None)
    return res


def set_download_link(curs, app: MinimalDetailApp, info: PathOnlyDownloadLink) -> None:
    curs.execute(
        "SELECT uid FROM app_detail WHERE id = %(id)s AND version_code = %(version_code)s AND offer_type = %(offer_type)s",
        {
            "id": app.id,
            "version_code": app.version_code,
            "offer_type": app.offer_type,
        },
    )
    app_record = curs.fetchone()
    curs.execute(
        "INSERT INTO apk (create_ts, app_detail_id, object_gz_path, object_gz_bytes, object_bytes, object_sha256_digest) VALUES (%(create_ts)s, %(app_detail_id)s, %(object_gz_path)s, %(object_gz_bytes)s, %(object_bytes)s, %(object_sha256_digest)s)",
        {
            "create_ts": info.created,
            "app_detail_id": app_record["uid"],
            "object_gz_path": info.apk_gz_url,
            "object_gz_bytes": info.apk_gz_bytes,
            "object_bytes": info.apk_bytes,
            "object_sha256_digest": info.sha256_digest,
        },
    )
