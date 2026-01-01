#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. $HOME/compute/tf_env.sh

export PYTHONPATH=$HOME/app_ingest/src
# Default port is 2025
python mcp_server_rag.py 2>&1 | tee mcp_server_rag.log
