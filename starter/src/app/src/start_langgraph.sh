#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

cd src/langgraph/app

# Start LangGraph CompiledStateGraph on port 2024
langgraph dev --host 0.0.0.0 2>&1 | tee ../langgraph.log

