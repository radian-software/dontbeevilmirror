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
  version_code BIGINT NOT NULL,
  version_string TEXT NOT NULL,
  offer_type INT NOT NULL,
  free_app BOOLEAN NOT NULL
);

CREATE TABLE apk(
  uid SERIAL PRIMARY KEY,
  create_ts TIMESTAMP NOT NULL,
  app_detail_id INT REFERENCES app_detail(uid),
  object_gz_path TEXT NOT NULL,
  object_gz_bytes BIGINT NOT NULL,
  object_bytes BIGINT NOT NULL,
  object_sha256_digest TEXT
);

-- migrate:down

DROP TABLE google_play_authentication;
DROP TABLE app_details;
DROP TABLE apk;
