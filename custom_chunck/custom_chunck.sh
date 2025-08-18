#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/..

cp -r custom_chunck/* starter/.
rm starter/custom_chunck.sh

cat starter/src/compute/app/shared_oci.append.py >> starter/src/compute/app/shared_oci.py
rm starter/src/compute/app/shared_oci.append.py

sed -i '/export TF_VAR_agent_datasource_ocid=/d' starter/src/compute/app/env.sh

echo >> starter/src/compute/app/requirements.txt
echo "# Docling" >> starter/src/compute/app/requirements.txt
echo langchain_docling >> starter/src/compute/app/requirements.txt

echo "http://www.gueury.com" > sample_files/gueury.crawler

# sed -i 's/export AGENT_DATASOURCE_OCID/TF_VAR_prefix="db23ai"/' starter/env.sh
# sed -i 's/TF_VAR_db_user="postgres"/TF_VAR_db_user="admin"/' starter/env.sh
# sed -i 's/POSTGRES/DB23ai/' starter/src/compute/app/requirements.txt

