#!/bin/bash
source ../../setoaikey.sh
source ../../setclaimcheck.sh
# if you pass in a parameter, use that as the task queue
# for the Open Account workflow
source ../../setsplitworkflows.sh $1
uv run python run_worker.py