# The web UI, built and served by nginx. Build context is the repository root
# (docker-compose.yml), so nginx.conf can be copied in next to the build output.

FROM node:26.12.0-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:1.31.6-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
