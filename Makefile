.PHONY: help

IMAGE_NAME ?= llvm-dash

help:
	@echo "$(IMAGE_NAME)"
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

_venv: requirements.txt bin/setup
	@bin/setup

docs: _venv bin/generate bin/index.py ## Generate docset
	@bin/generate
