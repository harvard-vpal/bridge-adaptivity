#!/usr/bin/env bash

python manage.py migrate --settings=config.settings.base
sleep 5 && /usr/local/bin/gunicorn config.wsgi:application -w 2 -b :8000 --log-file=/dev/stdout --log-level=info --access-logfile=/dev/stdout
