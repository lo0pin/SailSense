#!/bin/bash
cd /home/user/sailsense || exit 1
source .venv/bin/activate
PYTHONPATH=src python -m sailsense.display.oled_test
