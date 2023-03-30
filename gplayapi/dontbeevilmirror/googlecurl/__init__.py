import base64
from dataclasses import dataclass
import re
import subprocess
import urllib.parse


from requests.structures import CaseInsensitiveDict


@dataclass
class Response:
    status_code: int
    headers: CaseInsensitiveDict
    content: bytes


def request(
    method, url, *, data: (bytes | dict[str, str]) = b"", headers: dict[str, str] = {}
):
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
        if not CaseInsensitiveDict(headers).get("content-type"):
            headers = {
                **headers,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
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
        if not status_code_match:
            raise ValueError
        status_code = int(status_code_match.group(1))
    except (AttributeError, ValueError) as _:
        raise RuntimeError(
            f"unable to parse output from googlecurl subprocess: {repr(stderr)}"
        ) from None
    resp_headers = CaseInsensitiveDict()
    for key, value in re.findall(r"(?m)^header ([^:]+): (.+)", stderr):
        resp_headers[key] = value
    return Response(status_code, resp_headers, stdout)


def delete(url, *, data: (bytes | dict[str, str]) = b"", headers: dict[str, str] = {}):
    return request("DELETE", url, data=data, headers=headers)


def get(url, *, headers: dict[str, str] = {}):
    return request("GET", url, headers=headers)


def patch(url, *, data: (bytes | dict[str, str]) = b"", headers: dict[str, str] = {}):
    return request("PATCH", url, data=data, headers=headers)


def post(url, *, data: (bytes | dict[str, str]) = b"", headers: dict[str, str] = {}):
    return request("POST", url, data=data, headers=headers)


def put(url, *, data: (bytes | dict[str, str]) = b"", headers: dict[str, str] = {}):
    return request("PUT", url, data=data, headers=headers)
