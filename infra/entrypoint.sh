#!/bin/sh
# API container entrypoint: hand the mounted /data volume to the app user, then drop root.
# Some volumes mount as root, so the image's own chown does not reach them.
# Owner: A. Filled in by: A0.
set -eu
chown -R app:app /data
exec setpriv --reuid=app --regid=app --init-groups "$@"
