#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Java
sudo dnf install -y graalvm-25-jdk
sudo update-alternatives --set java /usr/lib64/graalvm/graalvm-java25/bin/java
echo "export JAVA_HOME=/usr/lib64/graalvm/graalvm-java25" >> $HOME/.bashrc

# Maven
sudo dnf install -y maven

# Build
export JAVA_HOME=/usr/lib64/graalvm/graalvm-java25
mvn package
