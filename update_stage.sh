#!/usr/bin/env bash

git reset --hard
git fetch
git checkout master
git pull

cd ./bridge_adaptivity

docker-compose -f ./docker-compose-stage.yml restart
