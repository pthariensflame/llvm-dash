.PHONY: help

IMAGE_NAME ?= llvm-dash
LLVM_PREFIX ?=
ASSUME_LUMEN_STYLE_BUILD ?= false

help:
	@echo "$(IMAGE_NAME)"
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

_venv: requirements.txt bin/setup
	@bin/setup

docs: _venv bin/generate bin/index.py ## Generate docset
	@env LLVM_PREFIX=$(LLVM_PREFIX) ASSUME_LUMEN_STYLE_BUILD=$(ASSUME_LUMEN_STYLE_BUILD) \
		bin/generate

tar:
	@env LLVM_PREFIX=$(LLVM_PREFIX) \
		bin/archive

reindex: clean-index docs ## Re-generate fresh index

clean: ## Clean generated html files
	@bin/clean documents

clean-index: ## Clean docset indices
	@bin/clean index

clean-all: ## Clean all builds
	@bin/clean all
