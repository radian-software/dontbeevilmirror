#!/usr/bin/env python3

import argparse
import base64
import gzip
import re
import subprocess
import sys

import flask


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=8443)
parser.add_argument("-u", "--upstream", type=str, default="android.clients.google.com")
args = parser.parse_args()


HTTP_METHODS = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH",
]

app = flask.Flask(__name__)


@app.route("/", defaults={"path": ""}, methods=HTTP_METHODS)
@app.route("/<path:path>", methods=HTTP_METHODS)
def proxy(path):
    query = ""
    if flask.request.query_string:
        query = "?" + str(flask.request.query_string)
    body = flask.request.get_data()
    print(f"{flask.request.method.upper()} https://{args.upstream}/{path}{query}")
    print(f"REQ BODY ({len(body)} chars): {body}")
    upstream_headers = {**flask.request.headers}
    upstream_headers["Host"] = args.upstream
    for key, val in upstream_headers.items():
        print(f"  {key}: {val}")
    cmd = [
        "googlecurl",
        "-X",
        flask.request.method,
        f"https://{args.upstream}/{path}{query}",
        *[f"-H{key}: {value}" for key, value in upstream_headers.items()],
        "--body",
        base64.b64encode(body),
        "--body-base64",
    ]
    upstream_resp = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if upstream_resp.returncode != 0:
        sys.stderr.buffer.write(upstream_resp.stderr)
        raise subprocess.CalledProcessError(
            returncode=upstream_resp.returncode, cmd=cmd
        )
    resp_body = upstream_resp.stdout
    status_code = int(
        re.search(r"(?m)^status ([0-9]+)", upstream_resp.stderr.decode()).group(  # type: ignore
            1
        )
    )
    upstream_resp_headers = {
        m[0]: m[1]
        for m in re.findall(r"(?m)^header ([^:]+): (.+)", upstream_resp.stderr.decode())
    }
    print(f"Got {status_code}")
    for key, val in upstream_resp_headers.items():
        print(f"  {key}: {val}")
    resp = flask.make_response(resp_body, status_code)
    for key, val in upstream_resp_headers.items():
        if key.lower() not in {"transfer-encoding", "content-length"}:
            resp.headers[key] = val
    nice_resp_body = resp_body
    if resp.headers.get("content-encoding") == "gzip":
        nice_resp_body = gzip.decompress(nice_resp_body)
    print(f"RES BODY ({len(nice_resp_body)} chars): {nice_resp_body}")
    return resp


# generate self-signed cert, e.g. with https://smallstep.com/cli/
#
# step certificate create localhost local.crt local.key --profile root-ca --no-password --insecure
app.run(host="127.0.0.1", port=args.port, ssl_context=("local.crt", "local.key"))
