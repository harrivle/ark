FROM python:3.8 AS builder


COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels/ -r requirements.txt

FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-dev \
&& rm -rf /var/lib/apt/lists/*

COPY ./Sybil ./Sybil
COPY --from=builder /wheels /wheels

RUN pip install --no-cache ./Sybil /wheels/* && rm -rf /wheels/

COPY . .
COPY ./models/snapshots/sybil/1P7rKz9Ir8Gd99AisaKLFddtS9uOczPG0.ckpt /root/.sybil/

EXPOSE 5000

ENTRYPOINT ["python", "main.py", "--config", "api/configs/sybil.json"]
