# PG14.24 / OS security base built by this repository (run 39796181991),
# retaining the official Immich VectorChord 0.4.3 payload.
FROM registry.cn-hangzhou.aliyuncs.com/pohvii/immich-postgres:14-vectorchord0.4.3-security-20261022@sha256:4483a3fbd807a9326f77d8a1f9e3b342285b32fd73d71756fef135210b26c76d

# Keep the PG major and vector extension ABI; update PostgreSQL itself and its
# OS security dependencies. PG14.24 contains the current PG14 security fixes.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    && apt-get install -y --no-install-recommends postgresql-14-pgvector \
    && version="$(postgres --version | awk '{print $3}')" \
    && test "${version%%.*}" = 14 \
    && dpkg --compare-versions "$version" ge 14.24 \
    && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' postgresql-14-pgvector)" ge 0.8.7 \
    && postgres --version \
    && test -f /usr/share/postgresql/14/extension/vchord.control \
    && rm -rf /var/lib/apt/lists/*
