FROM node:22-alpine AS build
WORKDIR /repo
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm nx build frontend

FROM nginx:1.27-alpine
COPY --from=build /repo/dist/apps/frontend /usr/share/nginx/html
EXPOSE 80
