FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inference.py main.py ./

RUN groupadd --gid 10003 inference \
    && useradd --uid 10003 --gid inference \
       --create-home --shell /usr/sbin/nologin inference

USER inference

CMD ["python", "main.py"]