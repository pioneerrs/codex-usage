.PHONY: setup demo check test doctor

setup:
	./scripts/bootstrap.sh

demo:
	./scripts/demo.sh

check:
	./scripts/check.sh

test:
	.venv/bin/python -m unittest discover -s tests

doctor:
	.venv/bin/python -m codex_usage doctor

