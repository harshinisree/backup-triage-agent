FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY runbooks ./runbooks
COPY data ./data
# Never run as root inside the container; the audit log is written to /app.
RUN useradd --create-home appuser && chown appuser /app
USER appuser
EXPOSE 5000
# gunicorn is a production web server. One worker, because incidents are kept in memory.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "triage.api:create_app()"]
