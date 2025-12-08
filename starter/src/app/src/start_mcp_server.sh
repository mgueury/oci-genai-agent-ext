#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

cd src/mcp_server
export PYTHONPATH=$HOME/app/src
# Default port is 9000
python mcp_server_rag.py 2>&1 | tee ../../mcp_server_rag.log
