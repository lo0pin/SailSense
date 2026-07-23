#!/bin/bash
cd /home/user/sailsense || exit 1
source .venv/bin/activate
SAILSENSE_WEATHER_STORAGE_INTERVAL=60 PYTHONPATH=src python -m sailsense.weather.weather_service_test
