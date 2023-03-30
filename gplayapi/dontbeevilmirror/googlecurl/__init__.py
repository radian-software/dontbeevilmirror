import base64
from dataclasses import dataclass
import re
import subprocess


from requests.structures import CaseInsensitiveDict


@dataclass
class Response:
    status_code: int
    headers: CaseInsensitiveDict
    content: bytes


def request(method, url, *, data=b"", headers={}):
    result = subprocess.run(
        [
            "googlecurl",
            "-X",
            method.upper(),
            url,
            *[f"-H{key}: {value}" for key, value in headers.items()],
            *(["--body", base64.b64encode(data), "--body-base64"] if data else []),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = result.stdout
    stderr = result.stderr.decode()
    status_code_match = re.search(r"(?m)^status ([0-9]+)", stderr)
    try:
        status_code = int(status_code_match.group(1))  # type: ignore
    except (AttributeError, ValueError) as _:
        raise RuntimeError(
            f"unable to parse output from googlecurl subprocess: {repr(stderr)}"
        ) from None
    resp_headers = CaseInsensitiveDict()
    for key, value in re.findall(r"(?m)^header ([^:]+): (.+)", stderr):
        resp_headers[key] = value
    return Response(status_code, resp_headers, stdout)


def delete(url, **kwargs):
    return request("DELETE", url, **kwargs)


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def patch(url, **kwargs):
    return request("PATCH", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)


def put(url, **kwargs):
    return request("PUT", url, **kwargs)
