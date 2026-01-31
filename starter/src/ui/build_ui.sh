#!/usr/bin/env bash
# Build_ui.sh
#
# Compute:
# - build the code 
# - create a $ROOT/compute/ui directory with the compiled files
# - and a start.sh to start the program
# Docker:
# - build the image
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/../../starter.sh env -no-auto
. $BIN_DIR/build_common.sh

build_ui

# LiveLabs
# Create a self signed certificate for the IP 
if [ "$APIGW_HOSTNAME" = "" ]; then
   cd $TARGET_DIR/compute
   if [ !-f $TARGET_DIR/compute/nginx_tls.conf ]; then
      # Nginx config
      mkdir -p $TARGET_DIR/compute
      cp nginx_tls.conf $TARGET_DIR/compute/.
      cd $TARGET_DIR/compute
      file_replace_variables nginx_tls.conf 

      # IP Certificate Request      
      cat << EOF     
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C = US
ST = State
L = City
O = Organization
CN = $COMPUTE_PUBLIC_IP

[req_ext]
subjectAltName = @alt_names

[alt_names]
IP.1 = $COMPUTE_PUBLIC_IP
EOF > san.cnf
      # Generate the key and the chain      
     openssl genrsa -out privkey.pem 2048
     openssl req -new -key privkey.pem -out server.csr -config san.cnf
     openssl x509 -req -in server.csr -signkey privkey.pem -out fullchain.pem -days 365 -extensions req_ext -extfile san.cnf
   fi
fi
