#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ../../env.sh

# User Interface with Streamlit
export PYTHONPATH=$HOME/app/src
streamlit run ui_mcp_client.py --server.port 8080 --global.logLevel=debug 2>&1 | tee ../../mcp_client.log

# Ex: curl "http://$BASTION_IP:8080/"
