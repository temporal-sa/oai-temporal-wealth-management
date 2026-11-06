#!/bin/bash
# uses default values if environment variables are not set.
[ -f ../../setclaimcheck.sh ] && source ../../setclaimcheck.sh
uv run uvicorn api.main:app --reload