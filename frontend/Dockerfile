# Build the static SPA. Caddy serves the resulting /dist (mounted via compose).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Export stage: the dist is consumed by the caddy service through the bind mount,
# but we also publish a tiny image in case you prefer serving it standalone.
FROM busybox:1.36 AS dist
COPY --from=build /app/dist /dist
