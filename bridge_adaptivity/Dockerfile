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

# Make sure entrypoint script is executable
RUN ["chmod", "+x", "run_container.sh"]

EXPOSE 8000

CMD ["./run_container.sh"]
