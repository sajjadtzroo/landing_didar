FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
# --legacy-peer-deps avoids an npm arborist peer-resolution crash on Nuxt's
# optional peer graph (npm 10.x). Safe: the Pinia stack is aligned on v3.
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
COPY --from=build /app/.output ./.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
