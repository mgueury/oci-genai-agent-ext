# -- Variables ---------------------------------------------

# Prefix to all resources created by terraform
prefix="__TO_FILL__"

# Min length 12 characters, 2 lowercase, 2 uppercase, 2 numbers, 2 special characters. Ex: LiveLab__12345
db_password="__TO_FILL__"

# BRING_YOUR_OWN_LICENSE or LICENSE_INCLUDED
license_model="__TO_FILL__"

# Compartment
compartment_ocid="__TO_FILL__"

# OCI Auth Token
auth_token="__TO_FILL__"

# RAG Storage 23ai
advanced="true"
rag_storage="db23ai"
vault_ocid="__TO_FILL__"
vault_key_ocid="__TO_FILL__"

# -- Fixed -------------------------------------------------
db_type="autonomous"
db_user="admin"
deploy_type="function"
language="java"
ui_type="html"

# Creation Details
OCI_STARTER_CREATION_DATE="2025-09-11-09-57-32-989263"
OCI_STARTER_VERSION="4.0"
OCI_STARTER_PARAMS="prefix,java_framework,java_vm,java_version,ui_type,db_type,license_model,mode,infra_as_code,db_password,oke_type,security,deploy_type,language"

