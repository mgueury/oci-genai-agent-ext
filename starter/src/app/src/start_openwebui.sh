#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh

# User Interface with Streamlit
cd src
open-webui serve --port 9999 2>&1 | tee ../openwebui.log

# Ex: curl "http://$BASTION_IP:8080/"
