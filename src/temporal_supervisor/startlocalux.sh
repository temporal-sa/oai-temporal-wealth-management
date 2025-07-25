#!/bin/bash
if [ -z "$1" ]; then
   echo "You must specify a workflow ID"
   exit 1
fi
source ../../setclaimcheck.sh
poetry run python run_supervisor.py --conversation-id $1
