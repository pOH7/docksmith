# Official Immich PG18 / VectorChord 1.1.1, pinned to its amd64 manifest.
FROM ghcr.io/immich-app/postgres:18-vectorchord1.1.1@sha256:fe112ee632f5d5b7cbee3d53d6c2d2d3ce91b8ad4288e5142aefc9961b853eab

# Apply current PostgreSQL, OS and pgvector security fixes before publication.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    && apt-get install -y --no-install-recommends postgresql-18-pgvector \
    && version="$(postgres --version | awk '{print $3}')" \
    && test "${version%%.*}" = 18 \
    && dpkg --compare-versions "$version" ge 18.6 \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' postgresql-18-pgvector)" ge 0.8.7 \
    && postgres --version \
    && test -f /usr/share/postgresql/18/extension/vchord.control \
    && rm -rf /var/lib/apt/lists/*
