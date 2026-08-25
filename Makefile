PY ?= python

.PHONY: setup test lint demo twin attack train stack evolve evaluate loop report api ui

setup:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

test:
	$(PY) -m pytest tests -v

lint:
	$(PY) -m ruff check src tests scripts

demo:
	$(PY) -m hydraloop demo

twin:
	$(PY) -m hydraloop twin

attack:
	$(PY) -m hydraloop attack

train:
	$(PY) -m hydraloop train

stack:
	$(PY) -m hydraloop stack

evolve:
	$(PY) -m hydraloop evolve

evaluate:
	$(PY) -m hydraloop evaluate

loop:
	$(PY) -m hydraloop loop

report:
	$(PY) scripts/build_reports.py

api:
	$(PY) -m hydraloop api

ui:
	cd ui && npm install && npm run dev
