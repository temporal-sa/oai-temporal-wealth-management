#!/bin/bash
echo "****************************************"
echo "* Remember to start your Redis Server! *"
echo "****************************************"
source ../../setclaimcheck.sh
poetry run python codec_server.py
