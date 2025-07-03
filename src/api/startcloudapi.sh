#!/bin/bash
source ../../setcloudenv.sh
poetry run uvicorn api.main:app --reload