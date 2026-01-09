#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

if [ -f shared_compute.sh ]; then
  # Docker mode
  . ./shared_compute.sh
  export TF_VAR_java_vm="jdk"
  # Do not install LubreOffice, the dependency makes the DockerImage 18GB
  export INSTALL_LIBREOFFICE="no"
fi

install_sqlcl

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
install_java

# Build Tika
cd src/tika
sudo dnf install -y maven
mvn package
cd -
