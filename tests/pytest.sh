#!/bin/bash

echo "Running Unit tests"

pytest -x --ff --random-order --cov=coingro_controller --cov-config=.coveragerc --cov-report=term --cov-report=html tests/
