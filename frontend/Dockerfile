# ── Stage 1: Build React app ──────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (layer cache)
COPY package.json ./
RUN npm install

# Copy source and build
# VITE_API_URL is set to the placeholder so we can inject it at runtime
# without rebuilding the image per environment.
COPY . .
ENV VITE_API_URL=__VITE_API_URL_PLACEHOLDER__
RUN npm run build

# ── Stage 2: Serve with Nginx ─────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config and built assets
COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Runtime env injection script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost/healthz || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
