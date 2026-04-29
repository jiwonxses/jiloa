# === Étape 1 : build ===
FROM node:20-alpine AS builder

WORKDIR /app

# Copier d'abord les fichiers de deps pour profiter du cache Docker
COPY package.json package-lock.json* ./
RUN npm install

# Copier le reste du code et build
COPY . .

# Variable d'environnement build-time pour l'URL du backend
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=$REACT_APP_API_URL

RUN npm run build

# === Étape 2 : runtime ===
FROM nginx:alpine

# Copier les fichiers statiques générés par Vite
COPY --from=builder /app/build /usr/share/nginx/html


# Copier la config Nginx custom
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]