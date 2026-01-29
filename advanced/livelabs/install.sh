#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

cd ../starter

cp ../advanced/* .
rm install.sh
mv ssrc/apigw.tf src/apigw._tf 
mv src/genai_apigw.tf src/genai_apigw._tf 
sed -i 's/oci_apigateway_/# oci_apigateway_" "kubernetes"/' src/terraform/build.tf 
