FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci && chown -R node:node /app/node_modules
COPY --chown=node:node . .
USER node
CMD ["npm","run","dev"]
