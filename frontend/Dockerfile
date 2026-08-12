FROM node:22-alpine AS build
WORKDIR /app
# Lockfile included so builds are reproducible — plain `npm install` from
# package.json alone re-resolves on every build and broke the moment upstream
# esbuild published a new binary (host/binary version mismatch).
COPY package.json package-lock.json ./
# --legacy-peer-deps avoids an npm arborist peer-resolution crash on Nuxt's
# optional peer graph (npm 10.x). Safe: the Pinia stack is aligned on v3.
# sharp@0.32 (via @nuxt/image → ipx) downloads libvips from GitHub releases,
# which hangs up from Liara's build network — use the npmmirror binary mirror.
ENV npm_config_sharp_libvips_binary_host="https://registry.npmmirror.com/-/binary/sharp-libvips"
RUN npm ci --legacy-peer-deps
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000
COPY --from=build /app/.output ./.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
