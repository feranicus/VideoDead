# Tiny exporter: pulls cookies from the Chromium container via the DevTools
# Protocol and writes a Netscape cookies.txt the worker reads. No browser here.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY export_cookies.py .
RUN useradd --uid 10002 jar && mkdir -p /cookies && chown jar /cookies
USER jar
CMD ["python", "export_cookies.py"]
