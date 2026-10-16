FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home appuser
USER appuser
EXPOSE 8107
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8107","--no-access-log"]
