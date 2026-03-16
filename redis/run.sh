#!/bin/sh

set -e

if [ -z "${REDIS_PASSWORD}" ]; then
    echo "Refusing to start redis without a password."
    exit 1
fi

mkdir -p /tmp/redis
redis-server --requirepass "${REDIS_PASSWORD}" --bind "0.0.0.0" "::" --port 8001 --dir /tmp/redis
