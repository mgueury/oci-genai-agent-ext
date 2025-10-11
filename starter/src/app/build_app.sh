#!/usr/bin/env bash
# Build_app.sh
#
# Compute:
# - build the code 
# - create a $ROOT/target/compute/$APP_DIR directory with the compiled files
# - and a start.sh to start the program
# Docker:
# - build the image
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. $SCRIPT_DIR/../../starter.sh env -no-auto
. $BIN_DIR/build_common.sh


## XXXXX Check Language version
get_attribute_from_tfstate "STREAM_OCID" "starter_stream" "id"
get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"
get_attribute_from_tfstate "STREAM_MESSAGE_ENDPOINT" "starter_stream" "messages_endpoint"
# Not used anymore ?
get_attribute_from_tfstate "STREAM_POOL_OCID" "starter_stream_pool" "id"
get_attribute_from_tfstate "STREAM_BOOSTRAPSERVER" "starter_stream_pool" "kafka_settings[0].bootstrap_servers"

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

echo
echo "-- STREAMING CONNECTION --------------------------"
echo "STREAM_MESSAGE_ENDPOINT=$STREAM_MESSAGE_ENDPOINT"
echo "STREAM_OCID=$STREAM_OCID"
echo "STREAM_USERNAME=$TENANCY_NAME/$TF_VAR_username/$STREAM_OCID"
echo
echo "-- AGENT (OPTIONAL) ---------------------------"
echo "TF_VAR_agent_datasource_ocid=$TF_VAR_agent_datasource_ocid"
echo "TF_VAR_agent_endpoint_ocid=$TF_VAR_agent_endpoint_ocid"

if is_deploy_compute; then
  mkdir -p ../../target/compute/$APP_DIR
  cp -r src/* ../../target/compute/$APP_DIR/.
  # Replace the user and password in the start file
  replace_db_user_password_in_file ../../target/compute/$APP_DIR/start.sh
  if [ -f $TARGET_DIR/compute/$APP_DIR/env.sh ]; then 
    if [ "$TF_VAR_agent_datasource_ocid" == "" ]; then
      export TF_VAR_agent_datasource_ocid="__NOT_USED__"
    fi
    if [ "$TF_VAR_install_libreoffice" == "" ]; then
      export TF_VAR_install_libreoffice="__NOT_USED__"
    fi
    if [ "$TF_VAR_rag_storage" == "" ]; then
      export TF_VAR_rag_storage="__NOT_USED__"
    fi
    file_replace_variables $TARGET_DIR/compute/$APP_DIR/env.sh
    exit_on_error "file_replace_variables"
  fi 
else
  docker image rm ${TF_VAR_prefix}-app:latest
  docker build -t ${TF_VAR_prefix}-app:latest .
  exit_on_error "docker build"
fi  


