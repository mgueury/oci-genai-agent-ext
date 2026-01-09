. $HOME/compute/tf_env.sh

# export DB_PASSWORD="##TF_VAR_db_password##"
# export DB_URL="##DB_URL##"
# export JDBC_URL="##JDBC_URL##"
# export APIGW_HOSTNAME="##APIGW_HOSTNAME##"

# # Generic
# export TF_VAR_compartment_ocid="##TF_VAR_compartment_ocid##"
# export TF_VAR_region="##TF_VAR_region##"
# export TF_VAR_prefix="##TF_VAR_prefix##"
# export OBJECT_STORAGE_NAMESPACE="##OBJECT_STORAGE_NAMESPACE##"

# # IDCS
# export IDCS_URL="##IDCS_URL##"

# # OCI Stream
# export STREAM_OCID="##STREAM_OCID##"
# export STREAM_MESSAGE_ENDPOINT="##STREAM_MESSAGE_ENDPOINT##"

# # OCI GenAI Agent
# export TF_VAR_agent_endpoint_ocid="##TF_VAR_agent_endpoint_ocid##"
# export TF_VAR_agent_datasource_ocid="##OPTIONAL/TF_VAR_agent_datasource_ocid##"
# export TF_VAR_genai_meta_model="##TF_VAR_genai_meta_model##"
# export TF_VAR_genai_cohere_model="##TF_VAR_genai_cohere_model##"
# export TF_VAR_genai_embed_model="##TF_VAR_genai_embed_model##"


export DB_USER="apex_app"
export TF_VAR_rag_storage="##OPTIONAL/TF_VAR_rag_storage##"

# LangFuse
# export LANGFUSE_PUBLIC_KEY=<your_public_key>
# export LANGFUSE_SECRET_KEY=<your_secret_key>
export LANGFUSE_HOST=http://localhost:3000


# export LANGSMITH_TRACING=true
# export LANGSMITH_TRACING=true
# export LANGSMITH_API_KEY=<your-api-key>
# export LANGSMITH_WORKSPACE_ID=agext

# Python VirtualEnv
if [ -d myenv ]; then
  source myenv/bin/activate
fi

# TNS_ADMIN
export TNS_ADMIN=$HOME/db

# During Initialisation - Store the env db in the database
# After Initialisation  - Use the env stored in the database as source of True
# Read Variables in database 
if [ "$1" != "INSTALL" ]; then
  if [ "$DB_URL" != "" ]; then
    $HOME/db/sqlcl/bin/sql $DB_USER/$DB_PASSWORD@DB <<EOF
      set linesize 1000
      set heading off
      set feedback off
      set echo off
      set verify off  
      spool /tmp/config.env
      select 'export TF_VAR_' || key || '="' || value || '"' from APEX_APP.AI_AGENT_RAG_CONFIG;
      spool off
EOF
  fi

  while read line; do
    if [ "$line" != "" ]; then
      eval $line
    fi
  done </tmp/config.env
  rm /tmp/config.env
fi

