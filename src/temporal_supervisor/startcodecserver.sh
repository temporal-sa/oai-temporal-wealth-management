#!/bin/bash
echo "****************************************"
echo "* Remember to start your Redis Server! *"
echo "****************************************"
[ -f ../../setclaimcheck.sh ] && source ../../setclaimcheck.sh
uv run python codec_server/codec_server.py
