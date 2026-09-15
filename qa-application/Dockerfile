FROM node:24.20.0-bookworm-slim AS dependencies

ENV CI=true

WORKDIR /app
RUN chown node:node /app

USER node

COPY --chown=node:node package.json package-lock.json ./
RUN npm ci


FROM dependencies AS development

COPY --chown=node:node . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


FROM development AS test

CMD ["sh", "-c", "npm run typecheck && npm run lint && npm run test:run && npm run build"]


FROM development AS build

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build


FROM nginx:1.28.0-alpine3.21 AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5173

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:5173/healthz"]
