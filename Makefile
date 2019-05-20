flake8:
	tox -e flake8

pytest:
	tox -e pytest

selenium:
	cd bridge_adaptivity && make test-selenium
