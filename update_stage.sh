#!/usr/bin/env bash

git reset --hard
git fetch
git checkout master
git pull

cd ./bridge_adaptivity

make migrate-stage
make run-stage
