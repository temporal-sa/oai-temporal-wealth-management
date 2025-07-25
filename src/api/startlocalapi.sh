#!/bin/bash
# uses default values if environment variables are not set.
source ../../setclaimcheck.sh
poetry run uvicorn api.main:app --reload