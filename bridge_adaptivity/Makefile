
COMPOSE_BASE := docker-compose -f docker-compose.yml


docker-build: .build/bridge .build/nginx

.build/bridge:
	docker build -t bridge_adaptivity .
	docker build --target=local -t bridge_adaptivity:local .
	docker build --target=stage -t bridge_adaptivity:stage .

.build/nginx: .build/bridge
	cd nginx \
	&& docker build \
		-t bridge-nginx . \
	&& docker build \
		--build-arg build_env=stage \
		-t bridge-nginx:stage .

run-local: docker-build
	$(COMPOSE_BASE) -f docker-compose_local.yml up -d bridge

run-stage: docker-build
	$(COMPOSE_BASE) -f docker-compose-stage.yml up -d

run:
	$(COMPOSE_BASE) up -d

stop-local:
	$(COMPOSE_BASE) -f docker-compose_local.yml stop

stop-stage:
	$(COMPOSE_BASE) -f docker-compose-stage.yml stop

stop:
	$(COMPOSE_BASE) stop

config-local:
	$(COMPOSE_BASE) -f docker-compose_local.yml config

config-stage:
	$(COMPOSE_BASE) -f docker-compose-stage.yml config

config-selenium:
	docker-compose -f docker-compose.yml -f docker-compose_local.yml -f docker-compose-selenium.yml config

config:
	$(COMPOSE_BASE) config

migrate-local:
	$(COMPOSE_BASE) -f docker-compose_local.yml run --entrypoint "" bridge python3 manage.py migrate

migrate-stage:
	$(COMPOSE_BASE) -f docker-compose-stage.yml run --entrypoint "" bridge python3 manage.py migrate

migrate:
	$(COMPOSE_BASE) run --entrypoint "" bridge python3 manage.py migrate

test-selenium: docker-build
	docker-compose -f docker-compose.yml -f docker-compose_local.yml -f docker-compose-selenium.yml run tests-functional
