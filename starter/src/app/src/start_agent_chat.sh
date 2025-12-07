#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

cd src/agent-chat-app/apps/web

# Start only the user interface
npm run dev 2>&1 | tee ../../../../agent-chat-app.log

# Ex: curl "http://$BASTION_IP:8080/"
