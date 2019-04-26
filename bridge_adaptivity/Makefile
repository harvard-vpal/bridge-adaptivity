
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
	docker-compose -f docker-compose.yml -f docker-compose_local.yml up -d bridge

run-stage: docker-build
	docker-compose -f docker-compose.yml -f docker-compose-stage.yml up -d

migrate:
	docker-compose -f docker-compose.yml run --entrypoint "" bridge python3 manage.py migrate

test-selenium: docker-build
	docker-compose -f docker-compose.yml -f docker-compose_local.yml -f docker-compose-selenium.yml run tests-functional
