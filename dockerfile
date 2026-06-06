FROM node:24-alpine AS frontend-builder
WORKDIR /code/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.13.5-slim
WORKDIR /code
COPY requirements.txt ./
RUN pip install uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -r requirements.txt

COPY --from=frontend-builder /code/frontend/dist ./static

COPY . .

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]