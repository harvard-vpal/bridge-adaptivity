FROM python:2.7
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y vim

RUN mkdir /bridge_adaptivity
WORKDIR /bridge_adaptivity
ADD . /bridge_adaptivity/

# Install requirements:
RUN pip install -U pip
RUN pip install -Ur requirements.txt

# Make static media dir:
RUN mkdir -p /www/static

COPY ./entrypoint.sh entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
