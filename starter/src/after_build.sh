#!/usr/bin/env bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./starter.sh env

get_attribute_from_tfstate "STREAM_OCID" "starter_stream" "id"
get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"
get_attribute_from_tfstate "STREAM_MESSAGE_ENDPOINT" "starter_stream" "messages_endpoint"
# Not used anymore ?
get_attribute_from_tfstate "STREAM_POOL_OCID" "starter_stream_pool" "id"
get_attribute_from_tfstate "STREAM_BOOSTRAPSERVER" "starter_stream_pool" "kafka_settings[0].bootstrap_servers"

get_attribute_from_tfstate "FN_OCID" "starter_fn_function" "id"
get_attribute_from_tfstate "FN_INVOKE_ENDPOINT" "starter_fn_function" "invoke_endpoint"

get_id_from_tfstate "TF_VAR_agent_datasource_ocid" "starter_agent_ds" 
get_id_from_tfstate "TF_VAR_agent_endpoint_ocid" "starter_agent_endpoint" 

get_id_from_tfstate "APP_SUBNET_OCID" "starter_app_subnet" 
get_id_from_tfstate "DB_SUBNET_OCID" "starter_db_subnet" 

oci generative-ai model-collection list-models --compartment-id $TF_VAR_compartment_ocid --all > $TARGET_DIR/genai_models.json 
export TF_VAR_genai_meta_model=$(jq -r '.data.items[]|select(.vendor=="meta" and (.capabilities|index("CHAT")))|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
echo $TF_VAR_genai_meta_model

export TF_VAR_genai_cohere_model=$(jq -r '.data.items[]|select(.vendor=="cohere" and (.capabilities|index("CHAT")))|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
echo $TF_VAR_genai_cohere_model

export TF_VAR_genai_embed_model="cohere.embed-multilingual-v3.0"
# export TF_VAR_genai_embed_model=$(jq -r '.data.items[]|select(.vendor=="cohere" and (.capabilities|index("TEXT_EMBEDDINGS")) and ."time-on-demand-retired"==null)|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
echo $TF_VAR_genai_embed_model

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
echo "TF_VAR_agent_datasource_ocid=$TF_VAR_agent_datasource_ocid"
echo "TF_VAR_agent_endpoint_ocid=$TF_VAR_agent_endpoint_ocid"

# Deploy compute simplified
mkdir -p $TARGET_DIR/compute/.
cp -r src/compute/* $TARGET_DIR/compute/.
if [ -f $TARGET_DIR/compute/app/env.sh ]; then 
  if [ "$TF_VAR_agent_datasource_ocid" == "" ]; then
    export TF_VAR_agent_datasource_ocid="__NOT_USED__"
  fi
  if [ "$TF_VAR_install_libreoffice" == "" ]; then
    export TF_VAR_install_libreoffice="__NOT_USED__"
  fi
  if [ "$TF_VAR_rag_storage" == "" ]; then
    export TF_VAR_rag_storage="__NOT_USED__"
  fi

  file_replace_variables $TARGET_DIR/compute/app/env.sh
  exit_on_error "after_build - file_replace_variables"
fi 
scp -r -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path $TARGET_DIR/compute/* opc@$BASTION_IP:/home/opc/.
ssh -o StrictHostKeyChecking=no -i $TF_VAR_ssh_private_path opc@$BASTION_IP "export TF_VAR_language=python;export AGENT_ENDPOINT_OCID=$AGENT_ENDPOINT_OCID;export AGENT_DATASOURCE_OCID=$AGENT_DATASOURCE_OCID;export FN_INVOKE_ENDPOINT=\"$FN_INVOKE_ENDPOINT\";export FN_OCID=\"$FN_OCID\";export STREAM_MESSAGE_ENDPOINT=\"$STREAM_MESSAGE_ENDPOINT\";export STREAM_OCID=\"$STREAM_OCID\";export DB_USER=\"$TF_VAR_db_user\";export DB_PASSWORD=\"$TF_VAR_db_password\";export DB_URL=\"$DB_URL\"; bash compute_bootstrap.sh 2>&1 | tee -a compute_bootstrap.log"

# Upload Sample Files
sleep 5
oci os object bulk-upload -ns $TF_VAR_namespace -bn ${TF_VAR_prefix}-public-bucket --src-dir ../sample_files --overwrite --content-type auto

title "INSTALLATION DONE"
echo
# echo "(experimental) Cohere with Tools and GenAI Agent:"
# echo "http://${BASTION_IP}:8081/"
# echo "-----------------------------------------------------------------------"
echo "TF_VAR_agent_endpoint_ocid=$TF_VAR_agent_endpoint_ocid"
echo
echo "-----------------------------------------------------------------------"
echo "Streamlit:"
echo "http://${BASTION_IP}:8080/"
echo
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
echo 
echo "-----------------------------------------------------------------------"
echo "Oracle Digital Assistant (Web Channel)"
echo "http://${BASTION_IP}"
echo 
