#!/bin/sh

pip3 install pipenv
pipenv install --dev
pipenv run pre-commit install
