#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. $HOME/compute/tf_env.sh INSTALL

# Python 
install_java

# orcl_db_sse
sudo firewall-cmd --zone=public --add-port=8081/tcp --permanent

