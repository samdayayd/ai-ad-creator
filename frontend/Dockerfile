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
# NEXT_PUBLIC_ vars are inlined into the client bundle at build time (unlike
# BACKEND_URL above, which only next.config.js's server-side rewrite reads).
# The browser uses this to call the backend directly for slow endpoints
# (video generation), bypassing the rewrite proxy's ~30s connection limit —
# see lib/api.ts's comment on BACKEND_URL for why that limit exists.
ARG NEXT_PUBLIC_BACKEND_URL
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
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
