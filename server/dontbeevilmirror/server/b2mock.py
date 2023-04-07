import os
import pathlib


class B2Mock:
    def __init__(self, storage):
        self.storage = storage

    def authorize_account(self, realm, key_id, key_secret):
        _ = realm
        _ = key_id
        _ = key_secret

    def get_bucket_by_name(self, name):
        return BucketMock(name, self.storage)


class BucketMock:
    def __init__(self, name, storage):
        self.name = name
        self.storage = pathlib.Path(storage) / name

    def upload_local_file(self, local_file, file_name, content_type):
        _ = content_type
        (self.storage / file_name).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.storage / file_name).hardlink_to(local_file)
