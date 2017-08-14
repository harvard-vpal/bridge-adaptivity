FROM python:2.7
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y vim

RUN mkdir /bridge-adaptivity
WORKDIR /bridge-adaptivity
ADD . /bridge-adaptivity/

# Install requirements:
RUN pip install -U pip
RUN pip install -Ur requirements.txt
RUN pip install -Ur requirements_local.txt

# Collect static media:
RUN mkdir -p /www/static
RUN python /bridge-adaptivity/manage.py collectstatic --noinput --settings=adaptive_edx.settings.base
