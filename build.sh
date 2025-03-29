#!/bin/bash
rm -rf dist
rm -rf build
rm -rf *.egg-info
./venv/bin/python3.12 setup.py sdist bdist_wheel