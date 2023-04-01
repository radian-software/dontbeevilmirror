import base64
from dataclasses import dataclass
import datetime
import json
import re
import struct
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import load_der_public_key
import _jsonnet
import requests

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
class InitialAuthInfo:

    auth: str
    token: str
    created: int


@dataclass
class AuthInfo:

    auth: str
    created: int


@dataclass
class CheckinInfo:

    android_id: str
    security_token: str
    consistency_token: str
    created: int


@dataclass
class SearchApp:

    id: str
    author: str
    name: str
    category: str
    downloads: int
    rating: float
    icon_url: str
    description: str
    screenshot_urls: list[str]
    free: bool
    price: str


@dataclass
class DetailApp:

    id: str
    version_code: str
    version_string: str
    offer_type: str
    free: bool


@dataclass
class DownloadLink:

    apk_gz_url: str
    apk_gz_bytes: int
    apk_bytes: int
    sha256_digest: str


class GooglePlay:
    email: str
    password: str
    auth_info: AuthInfo
    checkin_info: CheckinInfo

    def _do_initial_auth(self):
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
        self.initial_auth_info = InitialAuthInfo(
            auth=info["Auth"],
            token=info["Token"],
            created=int(datetime.datetime.now().timestamp()),
        )

    def _do_auth(self):
        resp = googlecurl.post(
            "https://android.clients.google.com/auth",
            data={
                "Authorization": f"GoogleLogin auth={self.initial_auth_info.auth}",
                "Token": self.initial_auth_info.token,
                "token_request_options": "CAA4AQ==",
                "service": "androidmarket",
                "accountType": "HOSTED_OR_GOOGLE",
                "app": "com.android.vending",
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
        self.auth_info = AuthInfo(
            auth=info["Auth"], created=int(datetime.datetime.now().timestamp())
        )

    def _populate_device_config(self, config):
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

    # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/Utils.java#L176-L203
    def _get_checkin_request(self):
        req: Any = pb.AndroidCheckinRequest()
        req.id = 0
        req.locale = "en_US"
        req.timeZone = "Europe/Berlin"
        req.version = 3
        req.fragment = 0
        checkin = req.checkin
        self._populate_device_config(req.deviceConfiguration)
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
                f"Got status code {resp.status_code} from /checkin endpoint"
            )
        resp_msg: Any = pb.AndroidCheckinResponse()
        resp_msg.ParseFromString(resp.content)
        self.checkin_info = CheckinInfo(
            android_id=f"{resp_msg.androidId:0{16}x}",
            security_token=f"{resp_msg.securityToken:0{16}x}",
            consistency_token=resp_msg.deviceCheckinConsistencyToken,
            created=int(datetime.datetime.now().timestamp()),
        )

    def _get_common_headers(self):
        return {
            "Accept-Language": "en-EN",
            "Authorization": f"GoogleLogin auth={self.auth_info.auth}",
            "X-DFE-Enabled-Experiments": "cl:billing.select_add_instrument_by_default",
            "X-DFE-Unsupported-Experiments": "nocache:billing.use_charging_poller,market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes",
            "X-DFE-Device-Id": self.checkin_info.android_id,
            "X-DFE-Client-Id": "am-android-google",
            # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/GooglePlayAPI.java#L154
            "User-Agent": "Android-Finsky/30.2.18-21 (api=3,versionCode=83021810,sdk=31,device=r9q,hardware=qcom,product=r9qxeea,platformVersionRelease=12,model=SM-G990B,buildId=SP1A.210812.016)",
            "X-DFE-SmallestScreenWidthDp": "320",
            "X-DFE-Filter-Level": "3",
        }

    def _do_upload_device_config(self):
        # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/GooglePlayAPI.java#L585-L590
        req: Any = pb.UploadDeviceConfigRequest()
        self._populate_device_config(req.deviceConfiguration)
        req.manufacturer = "Samsung"
        resp = googlecurl.post(
            "https://android.clients.google.com/fdfe/uploadDeviceConfig",
            data=req.SerializeToString(),
            headers={
                **self._get_common_headers(),
                "Content-Type": "application/x-protobuf",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /checkin endpoint"
            )

    def search(self, query: str):
        resp = requests.get(
            "https://play.google.com/store/search",
            params={
                "q": query,
                "c": "apps",
            },
        )
        match = re.search(r"(?s).*AF_initDataCallback\((.+?)\);</script>", resp.text)
        if not match:
            raise RuntimeError(
                "Failed to locate AF_initDataCallback in Google Play search response"
            )
        data = json.loads(_jsonnet.evaluate_snippet("snippet", match.group(1)))
        toplevel = data["data"][0][1][0][-1][0]
        apps = []
        for entry in toplevel:
            entry = entry[0]
            apps.append(
                SearchApp(
                    id=entry[0][0],
                    icon_url=entry[1][3][2],
                    screenshot_urls=[x[3][2] for x in entry[2]],
                    name=entry[3],
                    rating=entry[4][1],
                    category=entry[5],
                    free=entry[8][1][0][0] == 0,
                    price=entry[8][1][0][2],
                    description=entry[13][1],
                    author=entry[14],
                    downloads=entry[15],
                )
            )
        return apps

    def get_details_single(self, app_id: str):
        return self.get_details_multiple(app_id)[app_id]

    def get_details_multiple(self, *app_ids: str):
        # https://github.com/onyxbits/raccoon4/blob/923610fe8fadb6d7426283d99a7b0b4d538692f4/src/main/java/com/akdeniz/googleplaycrawler/GooglePlayAPI.java#L390-L397
        req: Any = pb.BulkDetailsRequest()
        req.docid.extend(app_ids)
        req.includeChildDocs = True
        resp = googlecurl.post(
            "https://android.clients.google.com/fdfe/bulkDetails",
            data=req.SerializeToString(),
            headers=self._get_common_headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /fdfe/bulkDetails endpoint"
            )
        resp_msg: Any = pb.ResponseWrapper()
        resp_msg.ParseFromString(resp.content)
        results = {}
        for entry in resp_msg.payload.bulkDetailsResponse.entry:
            doc = entry.doc
            app = DetailApp(
                id=doc.details.appDetails.packageName,
                version_code=doc.details.appDetails.versionCode,
                version_string=doc.details.appDetails.versionString,
                offer_type=doc.offer[0].offerType,
                free=doc.offer[0].micros == 0,
            )
            results[app.id] = app
        return results

    def _purchase(self, app: DetailApp):
        resp = googlecurl.post(
            "https://android.clients.google.com/fdfe/purchase",
            params={
                "doc": app.id,
                "vc": app.version_code,
                "ot": app.offer_type,
            },
            headers=self._get_common_headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /fdfe/delivery endpoint"
            )

    def get_download_link(self, app: DetailApp):
        resp = googlecurl.get(
            "https://android.clients.google.com/fdfe/delivery",
            params={
                "doc": app.id,
                "vc": app.version_code,
                "ot": app.offer_type,
            },
            headers=self._get_common_headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Got status code {resp.status_code} from /fdfe/delivery endpoint"
            )
        resp_msg: Any = pb.ResponseWrapper()
        resp_msg.ParseFromString(resp.content)
        data = resp_msg.payload.deliveryResponse.appDeliveryData
        if not data.downloadSize:
            raise RuntimeError(f"app {app.id} needs to be purchased before download")
        return DownloadLink(
            apk_gz_url=data.downloadUrlGzipped,
            apk_gz_bytes=data.downloadSizeGzipped,
            apk_bytes=data.downloadSize,
            sha256_digest=data.sha256,
        )
