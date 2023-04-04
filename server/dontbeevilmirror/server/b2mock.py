import pathlib


class B2Mock:
    def authorize_account(self, realm, key_id, key_secret):
        _ = realm
        _ = key_id
        _ = key_secret

    def get_bucket_by_name(self, name):
        return BucketMock(name)


class BucketMock:
    def __init__(self, name):
        self.name = name

    def upload_local_file(self, local_file, file_name, content_type):
        _ = content_type
        (pathlib.Path(".b2mock") / self.name).mkdir(parents=True, exist_ok=True)
        pathlib.Path(local_file).hardlink_to(
            pathlib.Path(".b2mock") / self.name / file_name
        )
