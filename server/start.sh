#!/usr/bin/env bash

set -euo pipefail

dbmate up

export PYTHONUNBUFFERED=1
exec gunicorn -b0.0.0.0:8080 -R --access-logfile=- dontbeevilmirror.server:app
