#!/bin/bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./env.sh

get_attribute_from_tfstate "STREAM_OCID" "starter_stream" "id"
get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"
get_attribute_from_tfstate "STREAM_MESSAGE_ENDPOINT" "starter_stream" "messages_endpoint"
# Not used anymore ?
get_attribute_from_tfstate "STREAM_POOL_OCID" "starter_stream_pool" "id"
get_attribute_from_tfstate "STREAM_BOOSTRAPSERVER" "starter_stream_pool" "kafka_settings[0].bootstrap_servers"

get_attribute_from_tfstate "FN_OCID" "starter_fn_function" "id"
get_attribute_from_tfstate "FN_INVOKE_ENDPOINT" "starter_fn_function" "invoke_endpoint"

get_id_from_tfstate "AGENT_DATASOURCE_OCID" "starter_agent_ds" 
get_id_from_tfstate "AGENT_ENDPOINT_OCID" "starter_agent_endpoint" 

get_id_from_tfstate "APP_SUBNET_OCID" "starter_app_subnet" 
get_id_from_tfstate "DB_SUBNET_OCID" "starter_db_subnet" 

echo 
echo "--------------------------"
echo "OCI SEARCH LAB Environment"
echo "--------------------------"
# echo "TENANCY_NAME=$TENANCY_NAME"
echo
echo "-- STREAMING CONNECTION --------------------------"
echo "STREAM_MESSAGE_ENDPOINT=$STREAM_MESSAGE_ENDPOINT"
echo "STREAM_OCID=$STREAM_OCID"
echo "STREAM_USERNAME=$TENANCY_NAME/$TF_VAR_username/$STREAM_OCID"
echo
echo "-- FUNCTION CONNECTION ---------------------------"
echo "FUNCTION_ENDPOINT=$FN_INVOKE_ENDPOINT/20181201/functions/$FN_OCID"
echo
echo "-- AGENT (OPTIONAL) ---------------------------"
echo "AGENT_DATASOURCE_OCID=$AGENT_DATASOURCE_OCID"
echo "AGENT_ENDPOINT_OCID=$AGENT_ENDPOINT_OCID"

# Deploy compute simplified
cp -r src/compute/* $TARGET_DIR/compute/.
scp -r -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path $TARGET_DIR/compute/* opc@$BASTION_IP:/home/opc/.
ssh -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path opc@$BASTION_IP "export TF_VAR_language=python;export AGENT_ENDPOINT_OCID=$AGENT_ENDPOINT_OCID;export AGENT_DATASOURCE_OCID=$AGENT_DATASOURCE_OCID;export FN_INVOKE_ENDPOINT=\"$FN_INVOKE_ENDPOINT\";export FN_OCID=\"$FN_OCID\";export STREAM_MESSAGE_ENDPOINT=\"$STREAM_MESSAGE_ENDPOINT\";export STREAM_OCID=\"$STREAM_OCID\";export DB_USER=\"$TF_VAR_db_user\";export DB_PASSWORD=\"$TF_VAR_db_password\";export DB_URL=\"$DB_URL\"; bash compute_bootstrap.sh 2>&1 | tee -a compute_bootstrap.log"

# Upload Sample Files
sleep 5
oci os object bulk-upload -ns $TF_VAR_namespace -bn ${TF_VAR_prefix}-public-bucket --src-dir ../sample_files --overwrite --content-type auto

echo "-----------------------------------------------------------------------"
echo "APEX login:"
echo
echo "APEX Workspace"
echo "https://${APIGW_HOSTNAME}/ords/_/landing"
echo "  Workspace: APEX_APP"
echo "  User: APEX_APP"
echo "  Password: $TF_VAR_db_password"
echo
echo "APEX APP"
echo "https://${APIGW_HOSTNAME}/ords/r/apex_app/apex_app/"
echo "  User: APEX_APP / $TF_VAR_db_password"
