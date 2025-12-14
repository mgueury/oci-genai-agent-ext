#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

cd src/orcl_db_sse

# Start only the user interface
MICRONAUT_SERVER_PORT=8081
./gradlew run 2>&1 | tee ../../orcl_db_sse.log
