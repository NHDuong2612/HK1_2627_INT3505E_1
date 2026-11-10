# ─── Stage 1: Builder ───
FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# ─── Stage 2: Runtime ───
FROM python:3.11-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app -d /app app
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app . .
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]