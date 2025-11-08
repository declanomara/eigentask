# Web (SvelteKit SSR)
FROM node:20-bullseye-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Ensure adapter-node is configured in svelte.config.js
RUN export $(grep -v '^#' ./public.env | xargs) && npm run build

FROM node:20-bullseye-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/build ./build
COPY package*.json ./
RUN npm ci --omit=dev
EXPOSE 3000
CMD ["node", "./build/index.js"]
