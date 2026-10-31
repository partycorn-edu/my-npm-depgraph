PYTHON ?= python3
CONFIG ?= config.toml

.PHONY: install test run demo clean

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

run:
	./run.sh -c $(CONFIG)

demo:
	sh scripts/demo_errors.sh
	sh scripts/demo_npm.sh
	sh scripts/demo_npm.sh examples/npm_errors

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
