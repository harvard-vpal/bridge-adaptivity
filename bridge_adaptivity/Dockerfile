FROM python:3.6
ENV PYTHONUNBUFFERED 1

WORKDIR /bridge_adaptivity
ADD . /bridge_adaptivity/

# Install requirements:
RUN pip install -r requirements.txt

EXPOSE 8000
