#!/bin/bash
# export TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT=Open-Account-Queue
if [ -z "$1" ]
  then
    echo "**** Missing required parameter: Task Queue Name for the Open Account Workflow"
    echo "(e.g. setting the TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT environment variable to match"
    echo "the same name when starting the python worker."
    exit 1
fi
export TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT="$1"
./gradlew runWorker