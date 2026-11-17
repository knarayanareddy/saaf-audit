# One image, one process, one URL.
#
# The frontend is built here rather than committed, so what runs is always built
# from the source in this repo — a dist/ folder someone forgot to rebuild is the
# classic way for a demo to show yesterday's app.

FROM node:20-slim AS frontend
WORKDIR /build
# package files first: this layer is cached unless the dependencies themselves
# change, which is most of the build time.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.13-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist /app/static

# The database and the uploads live on a mounted volume, never in the image:
# a container filesystem is replaced on every deploy, and audit evidence that
# disappears when you ship a fix is not evidence.
ENV IA_WINGMAN_DATA_DIR=/data \
    IA_WINGMAN_STATIC_DIR=/app/static \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# $PORT because most hosts assign one; the default keeps `docker run` simple.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
