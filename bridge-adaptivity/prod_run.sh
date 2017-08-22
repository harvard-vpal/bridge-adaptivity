#!/usr/bin/env bash

python manage.py migrate --settings=adaptive_edx.settings.base
sleep 5 && /usr/local/bin/gunicorn adaptive_edx.wsgi:application -w 2 -b :8000 --log-file=/dev/stdout --log-level=info --access-logfile=/dev/stdout

