FROM python:3.6 as prod_base
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    netcat \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

WORKDIR /bridge_adaptivity

COPY requirements_base.txt ./
COPY requirements.txt ./
RUN pip install -r requirements.txt

ENV DJANGO_SETTINGS_MODULE=config.settings.prod

FROM prod_base as stage_base

RUN apt-get update && apt-get install -y vim

RUN pip install -U pip
RUN pip install -Ur requirements.txt
# Make static media dir:
RUN mkdir -p /www/static

FROM stage_base as local_base

COPY requirements_local.txt ./
RUN pip install -r requirements_local.txt

FROM prod_base as prod

ENTRYPOINT ["gunicorn"]
CMD ["config.wsgi:application", "-w", "2", "-b", ":8000"]
COPY . .
RUN python manage.py collectstatic -v 3 -c --noinput

FROM local_base as local

ENV DJANGO_SETTINGS_MODULE=config.settings.local

ENTRYPOINT ["python", "manage.py"]
CMD ["runserver", "0.0.0.0:8000"]

COPY --from=prod /bridge_adaptivity /bridge_adaptivity
COPY --from=prod /www/static /www/static

FROM stage_base as stage

COPY --from=prod /bridge_adaptivity /bridge_adaptivity
COPY --from=prod /www/static /www/static

FROM prod
