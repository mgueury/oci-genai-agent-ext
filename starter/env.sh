#!/bin/bash

# Env Variables
export TF_VAR_prefix="agext"

export TF_VAR_ui_type="html"
export TF_VAR_db_type="autonomous"
export TF_VAR_license_model="__TO_FILL__"
export TF_VAR_deploy_type="function"
export TF_VAR_language="java"
export TF_VAR_db_user="admin"
# export TF_VAR_instance_shape="VM.Standard.E5.Flex"
# Convert Office files to PDF using LibreOffice (yes or no)
export INSTALL_LIBREOFFICE="yes"

# TF_VAR_compartment_ocid : ocid1.compartment.xxxxx
export TF_VAR_compartment_ocid="__TO_FILL__"
# TF_VAR_db_password : Min length 12 characters, 2 lowercase, 2 uppercase, 2 numbers, 2 special characters. Ex: LiveLab__12345
#   If not filled, it will be generated randomly during the first build.
export TF_VAR_db_password="__TO_FILL__"
# TF_VAR_auth_token : See doc: https://docs.oracle.com/en-us/iaas/Content/Registry/Tasks/registrygettingauthtoken.htm
export TF_VAR_auth_token="__TO_FILL__"

export TF_VAR_advanced="true"
if [ "$TF_VAR_advanced" == "true" ]; then
  export TF_VAR_rag_storage="db23ai"
  export TF_VAR_vault_ocid="__TO_FILL__"
  export TF_VAR_vault_key_ocid="__TO_FILL__"
fi

if [ -f $HOME/.oci_starter_profile ]; then
  . $HOME/.oci_starter_profile
fi

# Creation Details
export OCI_STARTER_CREATION_DATE=2025-05-14-16-21-43-942355
export OCI_STARTER_VERSION=3.7
export OCI_STARTER_PARAMS="prefix,java_framework,java_vm,java_version,ui_type,db_type,license_model,mode,infra_as_code,db_password,oke_type,deploy_type,language"



