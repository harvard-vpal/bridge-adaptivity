# Bridge for Adaptivity

A tool that interfaces with an adaptive engine to dynamically serve
content in MOOCs based on real time student activity.

Github wiki: https://github.com/harvard-vpal/bridge-adaptivity/wiki

Blog post: http://vpal.harvard.edu/blog/bridge-adaptivity-enabling-use-adaptive-assessments-edx

## Deployment

Deployment is based on the `Docker` containers. There are two config
files `docker-compose_local.yml` and `docker-compose.yml` for local
and production deployments respectively.

Docker and Docker Compose are required to be installed before start
the deploying.

Clone project.

Before running deployment configure `secure.py` settings in the
`bridge-adaptivity/adaptive_edx/settings/` directory (see `secure.py.example`).

### Local deployment

Local deployment can be started by the docker-compose up command in the
console:

    [sudo] docker-compose -f docker-compose_local.yml up

Local deployment contains two containers:

- BFA_local -- container with the Bridge for Adaptivity.

- postgresql_BFA -- container with the postgresql database.

  Volume "pgs" is added to the the database container.

  Note: Development server available on `localhost:8000`

### Production deployment

Please ensure that file in `nginx/sites_enabled/bridge.conf` exists and
is configured in proper way.

Run docker-compose up command with default `docker-compose.yml` file
to start production deployment:

    sudo docker-compose up -d

Production deployment contains three containers:

- BFA -- container with the the Bridge for Adaptivity.

  Bridge for Adaptivity application is running on gunicorn server.

- postgresql_BFA -- container with the postgresql database.

  Volume "pgs" is added to the the database container.

- nginx_BFA -- container with nginx server

### Additional notes

- if `requirements` changes were made containers rebuilding needed:

production:

    [sudo] docker-compose -f docker-compose.yml build

development:

    [sudo] docker-compose -f docker-compose_local.yml build
