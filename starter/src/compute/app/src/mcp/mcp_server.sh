#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. ../../env.sh

export PYTHONPATH=$HOME/app/src
python mcp_server_rag.py 2>&1 | tee ../../mcp_server_rag.log
