FROM node:24-alpine AS frontend-builder
WORKDIR /code/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.13.5-slim AS base
WORKDIR /code
COPY requirements.txt ./
RUN pip install --no-cache-dir uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

FROM base AS dev
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN uv pip install --upgrade pip
RUN uv pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["/bin/bash"]

FROM base AS production
ENV FLASK_ENV=production
ENV PORT=5000
RUN uv pip install --upgrade pip
RUN uv pip install --no-cache-dir -r requirements.txt
COPY --from=frontend-builder /code/frontend/dist ./static
COPY . .
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 5000
ENTRYPOINT ["/docker-entrypoint.sh"]
