FROM python:3.9.10-slim

ENV PYTHONUNBUFFERED 1

EXPOSE 8000
WORKDIR /app


RUN apt-get update && \
    apt-get install -y --no-install-recommends netcat && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY Pipfile.lock Pipfile ./
RUN pip install -q pipenv && \
    pipenv install

COPY . ./
RUN pipenv shell
CMD uvicorn --host=0.0.0.0 app.app:app