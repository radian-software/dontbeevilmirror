import os
import threading

import flask
import dotenv

dotenv.load_dotenv()

from dontbeevilmirror.server.copier import APKCopier
from dontbeevilmirror.server.gplay import GooglePlayWrapper

app = flask.Flask(__name__)
use_copier_mock = os.environ.get("B2_USE_MOCK") == "1"
copier_instance = APKCopier(
    os.environ["B2_KEY_ID"],
    os.environ["B2_KEY_SECRET"],
    os.environ["B2_BUCKET"],
    url_base="file://" if use_copier_mock else os.environ["B2_URL_BASE"],
    use_mock=use_copier_mock,
)
gplay = GooglePlayWrapper(os.environ["GOOGLE_EMAIL"], os.environ["GOOGLE_PASSWORD"])

if os.environ.get("ENABLE_BACKGROUND_JOBS") == "1":
    threading.Thread(
        name="gplay_authentication", target=gplay.maintain_authentication, daemon=True
    ).start()
    threading.Thread(
        name="b2_authentication",
        target=copier_instance.maintain_authentication,
        daemon=True,
    ).start()

from dontbeevilmirror.server import routes as _
