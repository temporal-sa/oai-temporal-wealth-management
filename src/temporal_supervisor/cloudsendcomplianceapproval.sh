#!/bin/bash
if [ -z "$1" ]; then
   echo "You must specify a workflow ID"
   exit 1
fi
source ../../setclaimcheck.sh
source ../../setcloudenv.sh
poetry run python run_send_compliance_approval.py --workflow-id $1