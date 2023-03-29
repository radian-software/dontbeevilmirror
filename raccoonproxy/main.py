#!/usr/bin/env python3

import argparse

import flask
import requests


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=8443)
parser.add_argument("-u", "--upstream", type=str, default="android.clients.google.com")
parser.add_argument("-k", "--insecure", action="store_true")
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
    upstream_resp = requests.request(
        flask.request.method,
        f"https://{args.upstream}/{path}{query}",
        headers=upstream_headers,
        data=body,
        verify=not args.insecure,
    )
    resp_body = b""
    for chunk in upstream_resp.raw.stream(1024, decode_content=False):
        if chunk:
            resp_body += chunk
    print(f"Got {upstream_resp.status_code}")
    for key, val in upstream_resp.headers.items():
        print(f"  {key}: {val}")
    resp = flask.make_response(resp_body, upstream_resp.status_code)
    for key, val in upstream_resp.headers.items():
        if key.lower() not in {"transfer-encoding", "content-length"}:
            resp.headers[key] = val
    print(f"RES BODY ({len(resp_body)} chars): {resp_body}")
    return resp


# generate self-signed cert, e.g. with https://smallstep.com/cli/
#
# step certificate create localhost local.crt local.key --profile root-ca --no-password --insecure
app.run(host="127.0.0.1", port=args.port, ssl_context=("local.crt", "local.key"))
