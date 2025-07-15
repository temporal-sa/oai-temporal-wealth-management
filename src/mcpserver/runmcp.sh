#!/bin/bash
#
# helper script to run the MCP Server
#
# To configure in Claude Desktop for testing,
# Add an entry to claude_desktop_config.json that looks like this:
#  "mcpServers": {
#    "wealth-management": {
#      "command": "/full/path/to/oai-wealth-management/src/mcpserver/runmcp.sh"
#    }
#  }
#
# Get the directory of the script
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
# go up two levels to where our .venv folder is located
cd "$SCRIPT_DIR/../.."
source .venv/bin/activate
/Users/rickross/.local/bin/poetry run python src/mcpserver/main.py

