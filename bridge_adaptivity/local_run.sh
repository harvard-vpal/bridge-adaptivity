#!/bin/bash
python manage.py collectstatic -v 3 -c --noinput
exec python manage.py runserver 0.0.0.0:8000
