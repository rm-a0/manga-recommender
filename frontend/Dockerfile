FROM node:24-alpine AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# Install dependencies in their own layer, so a source change does not
# reinstall them.
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# The runtime image holds only the standalone server and its static assets.
# No node_modules: `output: 'standalone'` traces and copies the files it needs.
FROM base AS runtime
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=build --chown=node:node /app/.next/standalone ./
# The standalone server serves these only when they sit next to it.
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000

# API_BASE_URL is read at request time on the server, so one image serves
# every environment. Container Apps sets it on the app.
CMD ["node", "server.js"]
