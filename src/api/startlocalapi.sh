#!/bin/bash
# uses default values if environment variables are not set.
poetry run uvicorn api.main:app --reload