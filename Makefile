.PHONY: lint
lint:
	pylint exman

.PHONY: pep8
pep8:
	pycodestyle exman

.PHONY: codestyle
codestyle: pep8 lint

.PHONY: configure
configure:
	if [ ! -f .git/hooks/pre-commit ]; then ln -s `pwd`/git-hooks/pre-commit .git/hooks/pre-commit; fi;

.PHONY: tests
tests:
	pytest tests
