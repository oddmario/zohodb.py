#!/bin/bash
python3 setup.py sdist
pip3 install ./dist/*.tar.gz
