#!/usr/bin/env bash
# Build_app.sh
#
# Compute:
# - build the code 
# - create a $ROOT/target/compute/$APP_NAME directory with the compiled files
# - and a start.sh to start the program
# Docker:
# - build the image
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/../../bin/build_common.sh

if is_deploy_compute; then
    build_rsync $APP_SRC_DIR
else
    OCI_CONFIG="$HOME/demo_user.txt"

    # Extract values
    user_ocid=$(grep '^user=' "$OCI_CONFIG" | cut -d'=' -f2-)
    fingerprint=$(grep '^fingerprint=' "$OCI_CONFIG" | cut -d'=' -f2-)

    # Extract the private key block as multiline value
    private_key=$(awk '/^-----BEGIN PRIVATE KEY-----/,/^OCI_API_KEY/' "$OCI_CONFIG")

    # Base64 encode everything (no line breaks for YAML compatibility)
    user_ocid_b64=$(printf '%s' "$user_ocid" | base64 | tr -d '\n')
    fingerprint_b64=$(printf '%s' "$fingerprint" | base64 | tr -d '\n')
    key_file_b64=$(printf '%s' "$private_key" | base64 | tr -d '\n')
    sed -i "s/##user_ocid_b64##/$user_ocid_b64/" k8s_litellm.yaml
    sed -i "s/##fingerprint_b64##/$fingerprint_b64/" k8s_litellm.yaml
    sed -i "s/##key_file_b64##/$key_file_b64/" k8s_litellm.yaml
fi  
