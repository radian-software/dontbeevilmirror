-- migrate:up

CREATE TABLE google_play_authentication(
  uid SERIAL PRIMARY KEY,
  create_ts TIMESTAMP NOT NULL,
  format_version INT NOT NULL,
  auth_data JSONB NOT NULL
);

CREATE TABLE app_detail(
  uid SERIAL PRIMARY KEY,
  create_ts TIMESTAMP NOT NULL,
  validate_ts TIMESTAMP NOT NULL,
  id TEXT NOT NULL,
  version_code TEXT NOT NULL,
  version_string TEXT NOT NULL,
  offer_type TEXT NOT NULL,
  free_app BOOLEAN NOT NULL
);

CREATE TABLE apk(
  uid SERIAL PRIMARY KEY,
  create_ts TIMESTAMP NOT NULL,
  app_id TEXT NOT NULL,
  version_code TEXT NOT NULL,
  offer_type TEXT NOT NULL,
  object_gz_path TEXT NOT NULL,
  object_gz_bytes BIGINT NOT NULL,
  object_bytes BIGINT NOT NULL,
  object_sha256_digest TEXT
);

-- migrate:down

DROP TABLE apk;
DROP TABLE app_detail;
DROP TABLE google_play_authentication;
