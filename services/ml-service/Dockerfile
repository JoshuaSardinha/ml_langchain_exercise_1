FROM python:3.11-slim AS build
WORKDIR /repo

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY services/ml-service/requirements.txt ./services/ml-service/
RUN pip install --no-cache-dir -r services/ml-service/requirements.txt

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY services/ml-service/app ./app

RUN mkdir -p data/models data/vectordb
EXPOSE 8000
CMD ["python", "-m", "app.main"]