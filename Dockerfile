FROM python:3.8-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential

ADD requirements.txt /

RUN pip install -r /requirements.txt

ADD test_app/ /

EXPOSE 8000/tcp

CMD hypercorn main:app