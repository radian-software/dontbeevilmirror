FROM golang:1.20 AS googlecurl

WORKDIR /src
COPY googlecurl/go.mod googlecurl/go.sum /src/
RUN go mod download
COPY googlecurl/main.go /src/
RUN go build

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y tini && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["tini", "--"]

RUN apt-get update && apt-get install -y python3-pip python3-venv && rm -rf /var/lib/apt/lists/*
RUN pip3 install "poetry>=1.4,<1.5"

RUN apt-get update && apt-get install -y protobuf-compiler && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
ADD https://github.com/amacneil/dbmate/releases/download/v2.2.0/dbmate-linux-amd64 /usr/local/bin/dbmate
RUN chmod +x /usr/local/bin/dbmate

RUN python3 -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /src
COPY gplayapi/pyproject.toml gplayapi/poetry.lock ./gplayapi/
RUN cd gplayapi && poetry install --no-root

COPY server/pyproject.toml server/poetry.lock ./server/
RUN cd server && poetry install --without=local --no-root

COPY --from=googlecurl /src/googlecurl /usr/local/bin/

COPY gplayapi/dontbeevilmirror/ ./gplayapi/dontbeevilmirror/
RUN cd /src/gplayapi/dontbeevilmirror/api && protoc google_play.proto --python_out=.

COPY server/dontbeevilmirror/ ./server/dontbeevilmirror/

ENV PYTHONPATH=/src/server:/src/gplayapi

RUN useradd -m -r -p! evil
USER evil

WORKDIR /src/server
COPY server/start.sh ./
COPY server/db/migrations ./db/migrations/
CMD ["./start.sh"]
EXPOSE 8080
