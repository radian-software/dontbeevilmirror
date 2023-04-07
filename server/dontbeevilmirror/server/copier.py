import gzip
import hashlib
import pathlib
from queue import Empty, Full, Queue
import shutil
import threading
import time
import uuid

from b2sdk.v2 import B2Api, InMemoryAccountInfo
import requests

from dontbeevilmirror.api import MinimalDetailApp, URLDownloadLink
from dontbeevilmirror.server import db, gplay_instance, logging
from dontbeevilmirror.server.b2mock import B2Mock


class NotAuthenticatedError(Exception):
    pass


class QueueFullError(Exception):
    pass


class APKCopier:
    def __init__(
        self,
        b2_key_id: str,
        b2_key_secret: str,
        bucket_name: str,
        url_base: str,
        use_mock=False,
    ):
        if use_mock:
            self.b2 = B2Mock()
        else:
            self.b2 = B2Api(InMemoryAccountInfo())
        self.url_prefix = url_base + bucket_name + "/"
        self.b2_key_id = b2_key_id
        self.b2_key_secret = b2_key_secret
        self.bucket_name = bucket_name
        self.b2_authenticated = False
        self.apk_copy_ratelimit = threading.BoundedSemaphore(3)
        self.has_authenticated = threading.Event()
        self.apk_queue_lock = threading.Lock()
        self.apk_active_set = set()
        self.apk_queue_set = set()
        self.apk_copy_queue = Queue(maxsize=15)

    def run_background_tasks(self) -> None:
        logging.info("Authenticating to B2")
        delay_after_failed_auth = 1
        while True:
            try:
                self.b2.authorize_account(
                    "production", self.b2_key_id, self.b2_key_secret
                )
                self.bucket = self.b2.get_bucket_by_name(self.bucket_name)
            except Exception as e:
                logging.error(
                    "Failed authenticating to B2",
                    extra={
                        "error": repr(e),
                        "delay_after_failed_auth": delay_after_failed_auth,
                    },
                )
                time.sleep(delay_after_failed_auth)
                delay_after_failed_auth *= 2
            else:
                self.b2_authenticated = True
                del self.b2_key_id
                del self.b2_key_secret
                logging.info("Authenticated to B2 successfully")
                break
        self.has_authenticated.set()
        while True:
            # Avoid busy-waiting, and make it easier to avoid race
            # conditions in most cases.
            time.sleep(1)

            try:
                if not self.apk_copy_ratelimit.acquire(blocking=False):
                    continue
            finally:
                self.apk_copy_ratelimit.release()

            with self.apk_queue_lock:
                try:
                    app = self.apk_copy_queue.get_nowait()
                    self.apk_queue_set.remove(app)
                except Empty:
                    continue

            def task():
                with self.apk_copy_ratelimit:
                    try:
                        logging.info(
                            "Downloading app",
                            extra={
                                "app": app,
                            },
                        )
                        with self.apk_queue_lock:
                            self.apk_active_set.add(app)
                        object_path = f"apks/{app.id}/${app.version_code}/${app.offer_type}/app.apk"
                        download = gplay_instance.get_download_link(app)
                        self._copy_apk(download, object_path)
                        with db.cursor() as curs:
                            db.set_download_link(
                                curs, app, download.with_path_only(object_path)
                            )
                    except Exception as e:
                        logging.warn(
                            "Failed to download app",
                            extra={
                                "app": app,
                                "error": repr(e),
                            },
                        )
                    finally:
                        self.apk_active_set.remove(app)

            threading.Thread(target=task, daemon=True).start()

    def request_app(self, app: MinimalDetailApp):
        if not self.has_authenticated.is_set():
            raise NotAuthenticatedError
        with self.apk_queue_lock:
            if app in self.apk_queue_set:
                return
            with db.cursor() as curs:
                if db.get_download_links(curs, app)[app.id]:
                    return
            try:
                self.apk_copy_queue.put_nowait(app)
                self.apk_queue_set.add(app)
            except Full:
                raise QueueFullError from None

    def get_app_status(self, app: MinimalDetailApp):
        with self.apk_queue_lock:
            with db.cursor() as curs:
                if db.get_download_links(curs, app)[app.id]:
                    return "available"
            if app in self.apk_active_set:
                return "downloading"
            if app in self.apk_queue_set:
                return "queued"
            return "unavailable"

    def _copy_apk(self, download_link: URLDownloadLink, object_path: str) -> None:
        tmp = pathlib.Path(f".tmp-apk-{str(uuid.uuid4())}")
        try:
            tmp.mkdir()
            with requests.get(download_link.apk_gz_url, stream=True) as resp:
                resp.raise_for_status()
                with open(tmp / "app.apk.gz", "wb+") as gz:
                    for chunk in resp.iter_content(chunk_size=8192):
                        gz.write(chunk)
                    digest = hashlib.sha256()
                    gz.seek(0)
                    with gzip.open(gz, "rb") as f:
                        while chunk := f.read(8192):
                            digest.update(chunk)
            if digest.hexdigest() != download_link.sha256_digest:
                raise RuntimeError("App digest mismatch")
            self.bucket.upload_local_file(
                tmp / "app.apk.gz", object_path, "application/gzip"
            )
        finally:
            shutil.rmtree(tmp)
