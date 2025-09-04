#!/bin/bash
#
# If you pass an optional argument to this script,
# there will be a Python workflow for the AI
# functionality and a Java Workflow for the
# Open Account Workflow
#
if [ ! -z "$1" ]
  then
    echo "*** Using $1 as the Task Queue for the Open Account workflow. ***"
    export TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT="$1"
    echo "*** Remember to also start the Java Workflow ***"
    echo "*** Also, the Java Workflow doesn't currently have a Payload converter"
    echo "*** which means that you need to disable the Claim Check"
fi