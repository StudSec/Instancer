FROM python:3.12.3-alpine
WORKDIR /app

RUN apk update && apk add bash

COPY requirements.txt /app

RUN mkdir -p /challenges && pip install --no-cache-dir -r /app/requirements.txt

COPY main.py /app
COPY webapp /app/webapp
COPY test/ /app

EXPOSE 8000
ENTRYPOINT [ "python", "main.py" ]
