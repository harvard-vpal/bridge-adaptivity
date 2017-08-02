# Bridge for Adaptivity

A tool that interfaces with an adaptive engine to dynamically serve
content in MOOCs based on real time student activity.

Github wiki: https://github.com/harvard-vpal/bridge-adaptivity/wiki

Blog post: http://vpal.harvard.edu/blog/bridge-adaptivity-enabling-use-adaptive-assessments-edx

## Deployment

Deployment is based on the `Docker` containers. There are two files in
the repository for local and production deployments `local-compose.yml`
and `docker-compose.yml` respectively.

Docker (Docker CE) and Docker Compose are required to be installed
before start deploying on local machine for local deployment and on
production server for production deployment.

1. [Guide for Docker installation on Ubuntu.](https://docs.docker.com/engine/installation/linux/ubuntu/#install-using-the-repository)

2. [Guide for Docker Compose installation on Ubuntu.](https://docs.docker.com/compose/install/)

After docker is installed clone project to the host machine (local or
prod).

### Local deployment

Local deployment is used for development and base testing. To run local
deployment use docker-compose up command in console:

`docker-compose -f local-compose.yml up`

Local deployment contains two containers:

- itero -- container with the Itero application.

  Itero application is running on default test server.

- postgres -- container with the database.

  Volume "pgdata" is added to the the database container.
