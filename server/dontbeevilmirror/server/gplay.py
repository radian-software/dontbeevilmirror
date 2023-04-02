import datetime
import threading
import time

from dontbeevilmirror.api import GooglePlay, SearchApp
from dontbeevilmirror.server import db
from dontbeevilmirror.server import logging
from dontbeevilmirror.server.util import now, rate_limit_with_timeout


class GooglePlayWrapper:

    MIN_LOGIN_DELAY = datetime.timedelta(seconds=5)
    MAX_LOGIN_DELAY = datetime.timedelta(hours=12)

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.gplay = GooglePlay()
        self.search_ratelimit = threading.BoundedSemaphore(5)
        self.auth_currently_working = False
        self.auth_needs_recheck = True
        self.login_allowed_after = datetime.datetime.fromtimestamp(0)
        self.delay_after_previous_login = GooglePlayWrapper.MIN_LOGIN_DELAY
        self.creds_need_saving = False
        self.creds_saving_allowed_after = datetime.datetime.fromtimestamp(0)

    def maintain_authentication(self):
        logging.info("Starting authentication loop")
        while True:
            try:
                with db.cursor() as curs:
                    creds = db.get_credentials(curs)
                    break
            except Exception as e:
                logging.error(
                    "Failed to fetch creds from db",
                    extra={
                        "error": repr(e),
                    },
                )
            time.sleep(5)
        logging.info(
            "Fetched creds from db",
            extra={
                "creds_present": bool(creds),
            },
        )
        if creds:
            self.gplay.set_credentials(creds)
        while True:
            # First, if we need to re-check authentication, we will do
            # so right away. Based on the result, we set
            # auth_currently_working to reflect the current state of
            # affairs. We also set auth_needs_recheck back to false
            # because there is no need to check authentication again
            # until we have tried logging in.
            if self.auth_needs_recheck:
                try:
                    if not self.gplay.has_credentials():
                        raise RuntimeError("Database didn't have credentials")
                    self.gplay.check_authentication()
                except Exception as e:
                    self.auth_currently_working = False
                    self.auth_needs_recheck = False
                    self.creds_need_saving = False
                    self.gplay.clear_credentials()
                    logging.warn(
                        "Authentication check failed",
                        extra={
                            "error": repr(e),
                        },
                    )
                else:
                    self.auth_currently_working = True
                    self.auth_needs_recheck = False
                    self.creds_need_saving = True
                    logging.info("Authentication check passed")
            # Now, if authentication is currently not working, but we
            # are allowed to try logging in (more on that later),
            # we'll do so. If we are able to login, then we queue up
            # an authentication check. Otherwise, we will just go
            # later.
            #
            # However, every time we try logging in, whether
            # successful or not, we also make sure that we do not try
            # logging in again too soon afterwards. This is
            # accomplished by a simplified version of exponential
            # backoff. If we keep having to log in, we wait twice as
            # long each time before the next attempt (regardless of
            # whether the attempts are successful or failed).
            if not self.auth_currently_working and (now() > self.login_allowed_after):
                self.login_allowed_after = now() + self.delay_after_previous_login
                self.delay_after_previous_login *= 2
                if self.delay_after_previous_login > GooglePlayWrapper.MAX_LOGIN_DELAY:
                    self.delay_after_previous_login = GooglePlayWrapper.MAX_LOGIN_DELAY
                try:
                    self.gplay.perform_initial_login(self.email, self.password)
                except Exception as e:
                    logging.warn(
                        "Login failed",
                        extra={
                            "error": repr(e),
                            "login_allowed_after": self.login_allowed_after,
                            "delay_after_previous_login": self.delay_after_previous_login,
                        },
                    )
                else:
                    self.auth_needs_recheck = True
                    logging.info(
                        "Login succeeded",
                        extra={
                            "login_allowed_after": self.login_allowed_after,
                            "delay_after_previous_login": self.delay_after_previous_login,
                        },
                    )
            # If on the other hand we have passed out of the waiting
            # period but we *don't* need to log in again, then we
            # start decreasing the waiting period back down to the
            # minimum.
            if (
                self.auth_currently_working
                and now() > self.login_allowed_after
                and self.delay_after_previous_login > GooglePlayWrapper.MIN_LOGIN_DELAY
            ):
                self.delay_after_previous_login /= 2
                if self.delay_after_previous_login < GooglePlayWrapper.MIN_LOGIN_DELAY:
                    self.delay_after_previous_login = GooglePlayWrapper.MIN_LOGIN_DELAY
                else:
                    self.login_allowed_after = now() + self.delay_after_previous_login
                logging.info(
                    "Decreased login cooldown interval",
                    extra={
                        "login_allowed_after": self.login_allowed_after,
                        "delay_after_previous_login": self.delay_after_previous_login,
                    },
                )
            # If we need to save the credentials to the db let's do
            # so. If it fails for some reason we'll keep trying every
            # 5 seconds, no need for exponential backoff with our own
            # database.
            if (
                self.auth_currently_working
                and self.creds_need_saving
                and now() > self.creds_saving_allowed_after
            ):
                try:
                    with db.cursor() as curs:
                        db.set_credentials(curs, self.gplay.get_credentials())
                except Exception as e:
                    self.creds_saving_allowed_after = now() + datetime.timedelta(
                        seconds=5
                    )
                    logging.error(
                        "Failed to save creds to db",
                        extra={
                            "error": repr(e),
                            "creds_saving_allowed_after": self.creds_saving_allowed_after,
                        },
                    )
                else:
                    self.creds_need_saving = False
            # Simple sanity sleep for the control loop. This isn't
            # really relevant to any rate limit, it's just to prevent
            # us from busy-waiting, because an event-driven
            # architecture would be unnecessarily complicated for our
            # use case here.
            time.sleep(1)

    def search(self, query: str) -> list[SearchApp]:
        with rate_limit_with_timeout(self.search_ratelimit, timeout_seconds=10):
            return self.gplay.search(query)
