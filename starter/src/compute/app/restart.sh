#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

sudo systemctl restart ingest
sudo systemctl restart streamlit
sudo systemctl restart tools
