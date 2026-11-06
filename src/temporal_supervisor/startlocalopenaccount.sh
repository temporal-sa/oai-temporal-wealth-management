#!/bin/bash
# Run the open-account workflow's three scenarios without the chat or the LLM
# (see run_open_account_workflow.py). Starts a local Python worker in the background
# for the activities (and, without a queue argument, the workflow too), without the
# OpenAI Agents plugin (SKIP_OPENAI_PLUGIN=True), and stops it when the scenarios finish.
# Usage: startlocalopenaccount.sh [open-account-task-queue]
# With a task queue name, the workflow runs on that queue: start the Java worker with
# the same name first (java/startlocalworker.sh <queue>).
cd "$(dirname "$0")" || exit 1
[ -f ../../setclaimcheck.sh ] && source ../../setclaimcheck.sh
[ -f ../../setoaikey.sh ] && source ../../setoaikey.sh
if [ -n "$1" ]; then
  export TEMPORAL_TASK_QUEUE_OPEN_ACCOUNT="$1"
  echo "*** Running the open-account workflow on task queue $1 (the Java worker must poll it). ***"
fi
export SKIP_OPENAI_PLUGIN=True
# The worker builds an OpenAI client at import time, which needs a key even though this
# run never calls the model. Use a placeholder if none is set.
export OPENAI_API_KEY="${OPENAI_API_KEY:-not-used-by-open-account-scenarios}"
echo "Starting the worker and running the three scenarios for the open-account workflow."
uv run python run_worker.py &
WORKER_PID=$!
trap 'kill $WORKER_PID 2>/dev/null; wait $WORKER_PID 2>/dev/null' EXIT
uv run python run_open_account_workflow.py
