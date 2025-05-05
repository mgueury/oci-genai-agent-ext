#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

uvicorn tools:app --host 0.0.0.0 --port 8081 2>&1 | tee tools.log