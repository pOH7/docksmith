# Official Immich PG14 / VectorChord 0.4.3 payload, mirrored unchanged.
FROM registry.cn-hangzhou.aliyuncs.com/pohvii/immich-postgres:14-vectorchord0.4.3@sha256:a2c92a8c3df39213ab41c926552353839e97cbe7751a4f8eee78215deec7727d

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
