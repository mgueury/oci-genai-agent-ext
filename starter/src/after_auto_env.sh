if grep -q 'STREAM_OCID' $TARGET_DIR/tf_env.sh; then
    echo "tf_env.sh already modified"
else 


    ## Set env variables needed for env.sh
    get_attribute_from_tfstate "STREAM_OCID" "starter_stream" "id"
    get_attribute_from_tfstate "TENANCY_NAME" "tenant_details" "name"
    get_attribute_from_tfstate "STREAM_MESSAGE_ENDPOINT" "starter_stream" "messages_endpoint"

    get_id_from_tfstate "TF_VAR_agent_datasource_ocid" "starter_agent_ds" 
    get_id_from_tfstate "TF_VAR_agent_endpoint_ocid" "starter_agent_endpoint" 

    get_id_from_tfstate "APP_SUBNET_OCID" "starter_app_subnet" 
    get_id_from_tfstate "DB_SUBNET_OCID" "starter_db_subnet" 

    append_tf_env "-- STREAMING CONNECTION -----------------------------"
    append_tf_env "export STREAM_MESSAGE_ENDPOINT=""$STREAM_MESSAGE_ENDPOINT"""
    append_tf_env "export STREAM_OCID=""$STREAM_OCID"""
    append_tf_env "export STREAM_USERNAME=""$TENANCY_NAME/$TF_VAR_username/$STREAM_OCID"""
    append_tf_env
    append_tf_env "-- AGENT (OPTIONAL) ---------------------------------"
    append_tf_env "export TF_VAR_agent_datasource_ocid=""$TF_VAR_agent_datasource_ocid"""
    append_tf_env "export TF_VAR_agent_endpoint_ocid=""$TF_VAR_agent_endpoint_ocid"""
    append_tf_env
    append_tf_env "-- GENERATIVE AI MODEL ------------------------------"
    oci generative-ai model-collection list-models --compartment-id $TF_VAR_compartment_ocid --all > $TARGET_DIR/genai_models.json 
    export TF_VAR_genai_meta_model=$(jq -r '.data.items[]|select(.vendor=="meta" and (.capabilities|index("CHAT")))|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
    append_tf_env "export TF_VAR_genai_meta_model=""$TF_VAR_genai_meta_model"""

    export TF_VAR_genai_cohere_model=$(jq -r '.data.items[]|select(.vendor=="cohere" and (.capabilities|index("CHAT")))|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
    append_tf_env "export TF_VAR_genai_cohere_model=""$TF_VAR_genai_cohere_model"""

    export TF_VAR_genai_embed_model="cohere.embed-multilingual-v3.0"
    # export TF_VAR_genai_embed_model=$(jq -r '.data.items[]|select(.vendor=="cohere" and (.capabilities|index("TEXT_EMBEDDINGS")) and ."time-on-demand-retired"==null)|.["display-name"]' $TARGET_DIR/genai_models.json | head -n 1)
    append_tf_env "export TF_VAR_genai_embed_model=""$TF_VAR_genai_embed_model"""
    
    append_tf_env export "TF_VAR_object_storage_url=""https://objectstorage.${TF_VAR_region}.oraclecloud.com/n/${TF_VAR_namespace}/b/${TF_VAR_prefix}-public-bucket/o/"""
fi