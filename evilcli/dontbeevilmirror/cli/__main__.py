import argparse
import os

import dotenv

from dontbeevilmirror import api

dotenv.load_dotenv()

parser = argparse.ArgumentParser("evilcli")
parser.add_argument("-u", "--email", "--username")
parser.add_argument("-p", "--password")
args = parser.parse_args()

email = args.email or os.environ.get("GOOGLE_EMAIL")
password = args.password or os.environ.get("GOOGLE_PASSWORD")

gplay = api.GooglePlay(email=email, password=password)
