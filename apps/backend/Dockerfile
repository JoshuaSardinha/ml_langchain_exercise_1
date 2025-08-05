FROM node:22-alpine AS build
WORKDIR /repo
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm nx build backend

FROM node:22-alpine
ENV NODE_ENV=production PORT=3000
WORKDIR /app
COPY --from=build /repo/dist/apps/backend ./dist
COPY --from=build /repo/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/main.js"]
