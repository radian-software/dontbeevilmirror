import os
import threading

import flask
import dotenv

from dontbeevilmirror.server.gplay import GooglePlayWrapper

dotenv.load_dotenv()

app = flask.Flask(__name__)
gplay = GooglePlayWrapper(os.environ["GOOGLE_EMAIL"], os.environ["GOOGLE_PASSWORD"])

threading.Thread(
    name="authentication", target=gplay.maintain_authentication, daemon=True
).start()

from dontbeevilmirror.server import routes as _
