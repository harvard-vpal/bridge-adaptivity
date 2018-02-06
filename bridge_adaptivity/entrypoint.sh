#!/usr/bin/env bash

# environment variables that can be set to control this entrypoint:
#   DJANGO_COLLECTSTATIC
#   DJANGO_MIGRATE
#   DJANGO_SETTINGS_MODULE
#   LEADER_ONLY

echo "LEADER_ONLY=$LEADER_ONLY"

# For multi-instance deployments, create /tmp/leader/is_leader (volume mount
# can be used) to denote the single container that should run admin commands

if [ -f /tmp/leader/is_leader ]; then
    IS_LEADER=1
    echo "Leader marker detected"
fi

if [[ -z $LEADER_ONLY || ( $LEADER_ONLY && $IS_LEADER) ]]; then
    if [ $DJANGO_COLLECTSTATIC ]; then
        python manage.py collectstatic -c --noinput
    else
        echo "Environment variable DJANGO_COLLECTSTATIC not set; skipping Django collectstatic"
    fi

    if [ $DJANGO_MIGRATE ]; then
        python manage.py migrate --noinput
    else
        echo "Environment variable DJANGO_MIGRATE not set; skipping Django migrate"
    fi
fi

if [ "$1" = "web" ] || [ -z "$1" ]; then
    echo "Starting web container ..."
    sleep 5 && /usr/local/bin/gunicorn config.wsgi:application -w 2 -b :8000 --log-file=/dev/stdout --log-level=info --access-logfile=/dev/stdout
elif [ "$1" = "worker" ]; then
    echo "Starting worker container..."
    celery -A config worker -l info
else
    echo "Command type not recognized"
    exit 1
fi
