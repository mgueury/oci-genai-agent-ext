#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

cd src/agent-chat-app

# User Interface with Streamlit and MCP
streamlit run ui_mcp_client.py --server.port 8080 2>&1 | tee ../../mcp_client.log

# Ex: curl "http://$BASTION_IP:8080/"
