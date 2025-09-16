export DB_USER="apex_app"
export DB_PASSWORD="##TF_VAR_db_password##"
export DB_URL="##DB_URL##"

export STREAM_OCID="##STREAM_OCID##"
export STREAM_MESSAGE_ENDPOINT="##STREAM_MESSAGE_ENDPOINT##"
export FN_OCID="##FN_OCID##"
export FN_INVOKE_ENDPOINT="##FN_INVOKE_ENDPOINT##"
export TF_VAR_compartment_ocid="##TF_VAR_compartment_ocid##"
export TF_VAR_region="##TF_VAR_region##"
export TF_VAR_agent_datasource_ocid="##TF_VAR_agent_datasource_ocid##"

# Streamlit Tools
export TF_VAR_agent_endpoint_ocid="##TF_VAR_agent_endpoint_ocid##"
export TF_VAR_prefix="##TF_VAR_prefix##"
export TF_VAR_namespace="##TF_VAR_namespace##"

# LibreOffice
export INSTALL_LIBREOFFICE="##TF_VAR_install_libreoffice##"

# GenAI_MODEL
export TF_VAR_genai_meta_model="##TF_VAR_genai_meta_model##"
export TF_VAR_genai_cohere_model="##TF_VAR_genai_cohere_model##"
export TF_VAR_genai_embed_model="##TF_VAR_genai_embed_model##"

# RAG Storage
export TF_VAR_rag_storage="##TF_VAR_rag_storage##"

# Python VirtualEnv
if [ -d $HOME/app/myenv ]; then
  source $HOME/app/myenv/bin/activate
fi

# During Initialisation - Store the env db in the database
# After Initialisation  - Use the env stored in the database as source of True
# Read Variables in database 
if [ "$1" != "INSTALL" ]; then
  if [ "$DB_URL" != "" ]; then
    export TNS_ADMIN=$HOME/db
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

