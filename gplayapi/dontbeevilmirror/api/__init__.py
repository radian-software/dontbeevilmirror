import base64
from dataclasses import dataclass
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.dsa import DSAPublicKey
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_der_public_key

from dontbeevilmirror import googlecurl


class GooglePublicKey:
    def __init__(self, raw_key_base64):
        self.raw_key = base64.b64decode(raw_key_base64)
        modulus_len = self._get_int_at(0, length=4)
        modulus = self._get_int_at(4, length=modulus_len)
        exponent_len = self._get_int_at(4 + modulus_len, length=4)
        exponent = self._get_int_at(4 + modulus_len + 4, length=exponent_len)
        self.public_key = load_der_public_key(encode_dss_signature(modulus, exponent))
        digest = hashes.Hash(hashes.SHA1())
        digest.update(self.raw_key)
        self.header = b"\x00" + digest.finalize()[:4]

    def _get_byte_at(self, index):
        return struct.unpack("B", bytes([self.raw_key[index]]))[0]

    def _get_int_at(self, start, *, length):
        res = 0
        for i in range(length):
            res <<= 8
            res |= self._get_byte_at(start + i)
        return res

    def encrypt(self, email, password):
        ciphertext = self.public_key.encrypt(  # type: ignore
            email.encode() + b"\x00" + password.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None,
            ),
        )
        return base64.urlsafe_b64encode(self.header + ciphertext)


GOOGLE_PUBLIC_KEY = GooglePublicKey(
    "AAAAgMom/1a/v0lblO2Ubrt60J2gcuXSljGFQXgcyZWveWLEwo6prwgi3iJIZdodyhKZQrNWp5nKJ3srRXcUW+F1BD3baEVGcmEgqaLZUNBjm057pKRI16kB0YppeGx5qIQ5QjKzsR8ETQbKLNWgRY0QRNVz34kMJR3P/LgHax/6rmf5AAAAAwEAAQ=="
)


@dataclass
class AuthInfo:

    auth: str
    token: str


class GooglePlay:
    def __init__(self, email, password):
        self.email = email
        self.password = password

    def login(self):
        pass

    def _do_auth(self):
        resp = googlecurl.post(
            "https://android.clients.google.com/auth",
            data={
                "Email": self.email,
                "EncryptedPasswd": GOOGLE_PUBLIC_KEY.encrypt(self.email, self.password),
                "service": "androidmarket",
                "add_account": "1",
                "sdk_version": "16",
                "accountType": "HOSTED_OR_GOOGLE",
                "hasPermission": "1",
                "source": "android",
                "app": "com.android.vending",
                "device_country": "en",
                "lang": "en",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /auth endpoint"
            )
        info = {}
        for line in resp.content.decode().splitlines():
            key, value = line.split("=", 1)
            info[key] = value
        return AuthInfo(auth=info["Auth"], token=info["Token"])
