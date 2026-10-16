FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3107
COPY --from=build --chown=node:node /app/.next-release/standalone ./
COPY --from=build --chown=node:node /app/.next-release/static ./.next-release/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3107
CMD ["node","server.js"]
