#!/usr/bin/env python3

import argparse
import gzip
import ssl

import flask
import requests
import requests.adapters
import urllib3.poolmanager
import urllib3.util.ssl_


JA3 = "769,49195-49196-52393-49199-49200-52392-158-159-49161-49162-49171-49172-51-57-156-157-47-53,65281-0-23-35-13-16-11-10,23,0"


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int, default=8443)
parser.add_argument("-u", "--upstream", type=str, default="android.clients.google.com")
parser.add_argument("-k", "--insecure", action="store_true")
args = parser.parse_args()


# https://github.com/marty0678/googleplay-api/blob/aa193ea198ac789f2b7d7a6650174078a93710a5/gpapi/googleplay.py#L46-L64


class GoogleSSLContext(ssl.SSLContext):
    def set_alpn_protocols(self, protocols):
        pass


class GoogleAuthHTTPAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = GoogleSSLContext()
        context.set_ciphers(urllib3.util.ssl_.DEFAULT_CIPHERS)
        context.verify_mode = ssl.CERT_REQUIRED
        context.options &= ~0x4000
        self.poolmanager = urllib3.poolmanager.PoolManager(
            *args, ssl_context=context, **kwargs
        )


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

session = requests.session()
session.mount("https://", GoogleAuthHTTPAdapter())

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
    upstream_resp = session.request(
        flask.request.method,
        f"https://{args.upstream}/{path}{query}",
        headers=upstream_headers,
        data=body,
        stream=True,
        **({"verify": False} if args.insecure else {}),
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
    nice_resp_body = resp_body
    if resp.headers["content-encoding"] == "gzip":
        nice_resp_body = gzip.decompress(nice_resp_body)
    print(f"RES BODY ({len(nice_resp_body)} chars): {nice_resp_body}")
    return resp


# generate self-signed cert, e.g. with https://smallstep.com/cli/
#
# step certificate create localhost local.crt local.key --profile root-ca --no-password --insecure
app.run(host="127.0.0.1", port=args.port, ssl_context=("local.crt", "local.key"))
