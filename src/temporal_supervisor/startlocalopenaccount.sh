#!/bin/bash
echo "This script starts the worker and kicks off the two scenarios for testing the open account workflow"
echo ""
echo "Remember to kill the startlocalworker.sh when finished"
echo ""
source ../../setclaimcheck.sh
export SKIP_OPENAI_PLUGIN=True
# Run the worker
./startlocalworker.sh &
poetry run python run_open_account_workflow.py