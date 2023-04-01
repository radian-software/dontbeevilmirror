import threading
import time

from dontbeevilmirror.api import GooglePlay, SearchApp
from dontbeevilmirror.server.util import rate_limit_with_timeout


class GooglePlayWrapper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.gplay = GooglePlay()
        self.search_ratelimit = threading.BoundedSemaphore(5)

    def maintain_authentication(self):
        while True:
            time.sleep(5)

    def search(self, query: str) -> list[SearchApp]:
        with rate_limit_with_timeout(self.search_ratelimit, timeout_seconds=10):
            return self.gplay.search(query)
