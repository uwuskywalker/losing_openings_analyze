FROM node:24-alpine AS frontend
WORKDIR /code
COPY package*.json ./
RUN npm install
COPY Frontend/ .
RUN npm run build

FROM python:3.13.5-slim
RUN pip install uv
RUN uv pip install -r requirements.txt

COPY --from=frontend /app/dist ./static

COPY . .

COPY entrypoint.sh docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]