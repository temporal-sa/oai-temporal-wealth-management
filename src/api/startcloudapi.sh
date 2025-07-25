#!/bin/bash
source ../../setclaimcheck.sh
source ../../setcloudenv.sh
poetry run uvicorn api.main:app --reload