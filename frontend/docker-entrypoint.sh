#!/bin/sh
# Replace the placeholder in the built JS with the runtime VITE_API_URL value.
# This lets the same Docker image run against any backend (dev, staging, prod)
# without a rebuild.
set -e

PLACEHOLDER="__VITE_API_URL_PLACEHOLDER__"
REPLACEMENT="${VITE_API_URL:-}"

echo "Injecting VITE_API_URL='${REPLACEMENT}' into built assets..."

find /usr/share/nginx/html -name "*.js" -exec \
  sed -i "s|${PLACEHOLDER}|${REPLACEMENT}|g" {} \;

echo "Done. Starting nginx..."
exec nginx -g "daemon off;"
