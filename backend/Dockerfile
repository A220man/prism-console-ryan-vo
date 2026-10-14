FROM python:3.12-slim

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin prism \
    && mkdir -p /data \
    && chown prism:prism /data

WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt
COPY backend/app /app/app
COPY VERSION /app/VERSION

USER prism
ENV PRISM_DB=/data/prism.sqlite
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
