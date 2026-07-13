# Multi-stage build for the Next.js standalone runtime (PLAYBOOK §6).
FROM node:20-alpine AS builder
WORKDIR /app
# Workspace install: root manifests + the packages this app consumes.
COPY package.json package-lock.json* ./
COPY web ./web
COPY packages ./packages
RUN npm install
# Placeholder envs so the build passes any startup validation without real secrets.
ENV ORCHESTRATOR_URL=http://localhost:8000 \
    NEXT_PUBLIC_APP_URL=http://localhost:3000
RUN npm run build --workspace web

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# Standalone output bundles only what the server needs.
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./web/.next/static
COPY --from=builder /app/web/public ./web/public
EXPOSE 3000
CMD ["node", "web/server.js"]
