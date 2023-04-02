import os
import threading

import flask
import dotenv

dotenv.load_dotenv()

from dontbeevilmirror.server.gplay import GooglePlayWrapper

app = flask.Flask(__name__)
gplay = GooglePlayWrapper(os.environ["GOOGLE_EMAIL"], os.environ["GOOGLE_PASSWORD"])

if os.environ.get("ENABLE_AUTHENTICATION_LOOP") == "1":
    threading.Thread(
        name="authentication", target=gplay.maintain_authentication, daemon=True
    ).start()

from dontbeevilmirror.server import routes as _
