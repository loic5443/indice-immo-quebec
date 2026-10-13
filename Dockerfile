FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home app \
    && mkdir -p /app/var && chown app:app /app/var
COPY --chown=app:app . .
USER app
EXPOSE 8501 8000
CMD ["python", "-m", "streamlit", "run", "indice_immo.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
