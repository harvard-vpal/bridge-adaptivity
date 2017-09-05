FROM python:2.7
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y vim

RUN mkdir /bridge_adaptivity
WORKDIR /bridge_adaptivity
ADD . /bridge_adaptivity/

# Install requirements:
RUN pip install -U pip
RUN pip install -Ur requirements.txt

# Collect static media:
RUN mkdir -p /www/static
RUN python manage.py collectstatic --noinput --settings=config.settings.base
