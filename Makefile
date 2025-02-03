# Makefile for the project. ease maintenance of code base
.PHONY: all test clean build

build:
	tar --exclude="*.pyc" --exclude="*__pycache" --exclude="*.pytest_cache" -cvf src/adgtk/template.tar project_template
	tar -cvf src/adgtk/clean.tar project_template/templates

all:
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.mypy_cache' -delete
	find . -type d -name '__pycache__' -delete
	tar --exclude="*.pyc" --exclude="*__pycache" --exclude="*.pytest_cache" -cvf src/adgtk/template.tar project_template
	tox

test:	
	tox

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type f -name '*.mypy_cache' -delete

backup:
	tar --exclude="*.pyc" --exclude="*__pycache" --exclude=".venv" --exclude=".tox" --exclude=".coverage" --exclude=".mypy_cache" --exclude=".pytest_cache" --exclude="adgtk.tar.gz" --exclude=".vscode" --exclude="tmp-results" --exclude=".git" --exclude="./build" --exclude="./dist" -czvf adgtk.tar.gz  .
	mv adgtk.tar.gz ../
