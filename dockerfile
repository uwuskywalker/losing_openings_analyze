FROM node:24-alpine AS frontend-builder
WORKDIR /code/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.13.5-slim AS production
WORKDIR /code
COPY requirements.txt ./
# Install uv and create virtual environment using uv
RUN pip install --no-cache-dir uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
# Use uv's pip to upgrade pip and install requirements inside the uv-managed venv
RUN uv pip install --upgrade pip
RUN uv pip install --no-cache-dir -r requirements.txt

COPY --from=frontend-builder /code/frontend/dist ./static

COPY . .

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

FROM python:3.13.5-slim AS dev
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY requirements.txt ./
# Install uv and create virtual environment using uv for dev
RUN pip install --no-cache-dir uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN uv pip install --upgrade pip
RUN uv pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["/bin/bash"]
