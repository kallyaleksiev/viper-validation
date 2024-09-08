# Makefile

.PHONY: format lint type-check test all

VIPV_SRC := ./src

format:
	isort $(VIPV_SRC)
	black $(VIPV_SRC)

format-check:
	isort --check-only $(VIPV_SRC)
	black --check $(VIPV_SRC)

lint:
	flake8 $(VIPV_SRC)

type-check:
	mypy $(VIPV_SRC)

check: format-check type-check lint