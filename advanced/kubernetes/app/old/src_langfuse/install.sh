#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Podman Compose
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm -y
sudo dnf install -y git podman-compose

# LangFuse
git clone https://github.com/langfuse/langfuse.git
# sudo dnf -y install oraclelinux-developer-release-el8