import gzip
import hashlib
import pathlib
import shutil
import threading
import time
import uuid

from b2sdk.v2 import B2Api, InMemoryAccountInfo
import requests

from dontbeevilmirror.api import URLDownloadLink
from dontbeevilmirror.server import logging
from dontbeevilmirror.server.b2mock import B2Mock


class TimeoutDueToAuthError(Exception):
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

    def maintain_authentication(self) -> None:
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

    def _copy_apk(self, download_link: URLDownloadLink, object_path: str) -> None:
        if not self.has_authenticated.wait(timeout=300):
            raise TimeoutDueToAuthError
        with self.apk_copy_ratelimit:
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
