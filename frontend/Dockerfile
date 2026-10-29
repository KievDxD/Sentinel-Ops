FROM node:20-alpine AS etapa_compilacion

WORKDIR /aplicacion_frontend

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS etapa_produccion

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=etapa_compilacion /aplicacion_frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

