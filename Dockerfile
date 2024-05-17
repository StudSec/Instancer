FROM python:3.12.3-alpine
WORKDIR /app

COPY requirements.txt /app
RUN mkdir -p /challenges && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000
ENTRYPOINT [ "python", "main.py" ]
