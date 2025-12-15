#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

cd src/orcl_db_sse

# Start only the user interface
./gradlew bootRun 2>&1 | tee ../../orcl_db_sse.log
