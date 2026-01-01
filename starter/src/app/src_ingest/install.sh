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
if [ ! -f /tmp/wkhtmltox-0.12.6-1.centos8.x86_64.rpm ]; then
    download https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm 
    sudo dnf localinstall -y wkhtmltox-0.12.6-1.centos8.x86_64.rpm
    mv *.rpm /tmp
fi

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
