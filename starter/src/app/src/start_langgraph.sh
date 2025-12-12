#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

cd src/langgraph/app

# export LANGSMITH_TRACING=true
# export LANGSMITH_API_KEY=<your-api-key>
# export LANGSMITH_WORKSPACE_ID=agext

# Start LangGraph CompiledStateGraph on port 2024
langgraph dev --host 0.0.0.0 2>&1 | tee ../../../langgraph.log

