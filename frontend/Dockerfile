FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# next.config.js's rewrites() is resolved when `next build` runs, not when the
# container later starts, so BACKEND_URL must be available here at build
# time — a plain runtime dashboard env var never reaches it. Render (and most
# Docker-based hosts) auto-forward an environment variable as a build
# --build-arg when a Dockerfile ARG of the same name exists.
ARG BACKEND_URL
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Docker sets its own HOSTNAME env var to the container ID, which the Next.js
# standalone server reads as its bind address if present, silently binding to
# an address nothing outside the container can reach. Force it to bind
# everywhere instead.
ENV HOSTNAME="0.0.0.0"
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
