FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Run Cloud Sync as a non-root user in Core's shared data group.
RUN groupadd --gid 10000 gsdata \
    && useradd --uid 10002 --gid gsdata \
       --create-home --shell /usr/sbin/nologin cloudsync

USER cloudsync

CMD ["python", "-m", "app.main"]
