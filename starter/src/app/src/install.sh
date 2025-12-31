#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. ./env.sh INSTALL

function download()
{
   echo "Downloading - $1"
   wget -nv $1
}

# Anonymize
sudo dnf install -y poppler-utils mesa-libGL

# Python 
install_python

# PDFKIT
download https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm
sudo dnf localinstall -y wkhtmltox-0.12.6-1.centos8.x86_64.rpm
mv *.rpm /tmp

# LibreOffice (convert docx to PDF)
if [ "${INSTALL_LIBREOFFICE}" != "no" ]; then
    install_libreoffice
    # Chrome + Selenium to get webpage
    install_chrome
fi 
cd $SCRIPT_DIR

# Java
sudo dnf install -y graalvm-25-jdk maven
sudo update-alternatives --set java /usr/lib64/graalvm/graalvm-java25/bin/java
echo "export JAVA_HOME=/usr/lib64/graalvm/graalvm-java25" >> $HOME/.bashrc

# Build Tika
export JAVA_HOME=/usr/lib64/graalvm/graalvm-java25
cd src/tika
mvn package
cd -

# MCP 
sudo firewall-cmd --zone=public --add-port=2025/tcp --permanent

# Langgraph
sudo firewall-cmd --zone=public --add-port=2024/tcp --permanent

# orcl_db_sse
sudo firewall-cmd --zone=public --add-port=8081/tcp --permanent

# Node (JET/Angular/ReactJS)
sudo dnf module enable -y nodejs:20
sudo dnf install -y nodejs

# Agent Chat UI
cd src
npx create-agent-chat-app -Y --project-name agent-chat-app --package-manager npm 
sed -i "s/next dev/next dev -p 8080/" agent-chat-app/apps/web/package.json

# Podman Compose
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm -y
sudo dnf install -y git podman-compose

# LangFuse
git clone https://github.com/langfuse/langfuse.git
# sudo dnf -y install oraclelinux-developer-release-el8