FROM python:3.6
ENV PYTHONUNBUFFERED 1

WORKDIR /bridge_adaptivity

# Install requirements:
COPY requirements.txt .
RUN pip install -r requirements.txt

ADD . /bridge_adaptivity/

EXPOSE 8000
