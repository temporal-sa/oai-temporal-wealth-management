#!/bin/bash
source ../../setclaimcheck.sh
source ../../setcloudenv.sh
uv run uvicorn api.main:app --reload