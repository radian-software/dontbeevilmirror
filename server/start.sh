#!/usr/bin/env bash

set -euo pipefail

dbmate up
exec gunicorn -b0.0.0.0:8080 dontbeevilmirror.server:app
