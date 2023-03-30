import base64
from dataclasses import dataclass
import datetime
import struct
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_der_public_key

from dontbeevilmirror import googlecurl
from dontbeevilmirror.api import constants
from dontbeevilmirror.api import google_play_pb2 as pb


class GooglePublicKey:
    def __init__(self, raw_key_base64):
        self.raw_key = base64.b64decode(raw_key_base64)
        modulus_len = self._get_int_at(0, length=4)
        modulus = self._get_int_at(4, length=modulus_len)
        exponent_len = self._get_int_at(4 + modulus_len, length=4)
        exponent = self._get_int_at(4 + modulus_len + 4, length=exponent_len)
        self.public_key: Any = load_der_public_key(
            encode_dss_signature(modulus, exponent)
        )
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
        ciphertext = self.public_key.encrypt(
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


@dataclass
class CheckinInfo:

    android_id: str
    security_token: str
    consistency_token: str


class GooglePlay:
    def __init__(self):
        self.email = None
        self.password = None
        self.auth_info = None

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
        self.auth_info = AuthInfo(auth=info["Auth"], token=info["Token"])

    # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/Utils.java#L176-L203
    def _get_checkin_request(self):
        req: Any = pb.AndroidCheckinRequest()
        req.id = 0
        req.locale = "en_US"
        req.timeZone = "Europe/Berlin"
        req.version = 3
        req.fragment = 0
        checkin = req.checkin
        config = req.deviceConfiguration
        checkin.lastCheckinMsec = 0
        checkin.cellOperator = "310260"
        checkin.simOperator = "310260"
        checkin.roaming = "mobile-notroaming"
        checkin.userNumber = 0
        build = checkin.build
        build.id = (
            "samsung/r9qxeea/r9q:12/SP1A.210812.016/G990BXXU1BUL5:user/release-keys"
        )
        build.product = "r9qxeea"
        build.carrier = "Google"
        build.radio = "I9300XXALF2"
        build.bootloader = "G990BXXU1BUL5"
        build.client = "android-google"
        build.timestamp = int(datetime.datetime.now().timestamp())
        build.googleServices = 16
        build.device = "r9q"
        build.sdkVersion = 31
        build.model = "SM-G990B"
        build.manufacturer = "samsung"
        build.buildProduct = "r9qxeea"
        build.otaInstalled = False
        config: Any = pb.DeviceConfigurationProto()
        config.touchScreen = 3
        config.keyboard = 1
        config.navigation = 1
        config.screenLayout = 2
        config.hasHardKeyboard = False
        config.hasFiveWayNavigation = False
        config.screenDensity = 480
        config.glEsVersion = 196610
        config.systemSharedLibrary.extend(constants.SYSTEM_SHARED_LIBRARIES)
        config.systemAvailableFeature.extend(constants.SYSTEM_AVAILABLE_FEATURES)
        config.nativePlatform.extend(["arm64-v8a", "armeabi-v7a", "armeabi"])
        config.screenWidth = 1080
        config.screenHeight = 2097
        config.systemSupportedLocale.extend(constants.SYSTEM_SUPPORTED_LOCALES)
        config.glExtension.extend(constants.GL_EXTENSIONS)
        return req

    def _do_checkin(self):
        # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/GooglePlayAPI.java#L508-L512
        resp = googlecurl.post(
            "https://android.clients.google.com/checkin",
            data=self._get_checkin_request().SerializeToString(),
            headers={
                "User-Agent": "Android-Checkin/2.0 (generic JRO03E); gzip",
                "Content-Type": "application/x-protobuffer",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /auth endpoint"
            )
        resp_msg: Any = pb.AndroidCheckinResponse()
        resp_msg.ParseFromString(resp.content)
        self.checkin_info = CheckinInfo(
            android_id=f"{resp_msg.androidId:0{16}x}",
            security_token=f"{resp_msg.securityToken:0{16}x}",
            consistency_token=resp_msg.deviceCheckinConsistencyToken,
        )
