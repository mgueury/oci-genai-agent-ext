#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

. ./env.sh INSTALL

function download()
{
   echo "Downloading - $1"
   wget -nv $1
}

# Anonymize
sudo dnf install -y poppler-utils mesa-libGL

# Python 
sudo dnf install -y python3.12 python3.12-pip python3-devel wget
sudo update-alternatives --set python /usr/bin/python3.12
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv myenv
source myenv/bin/activate
uv pip install -r src/requirements.txt

# PDFKIT
download https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox-0.12.6-1.centos8.x86_64.rpm
sudo dnf localinstall -y wkhtmltox-0.12.6-1.centos8.x86_64.rpm
mv *.rpm /tmp

# LibreOffice (convert docx to PDF)
if [ "${INSTALL_LIBREOFFICE}" != "no" ]; then
    sudo dnf group install -y "Server with GUI"
    cd /tmp
    export STABLE_VERSIONS=`curl -s https://download.documentfoundation.org/libreoffice/stable/`
    export LIBREOFFICE_VERSION=`echo $STABLE_VERSIONS | sed 's/.*<td valign="top">//' | sed 's/\/<\/a>.*//' | sed 's/.*\/">//'`
    echo LIBREOFFICE_VERSION=$LIBREOFFICE_VERSION

    download https://download.documentfoundation.org/libreoffice/stable/${LIBREOFFICE_VERSION}/rpm/x86_64/LibreOffice_${LIBREOFFICE_VERSION}_Linux_x86-64_rpm.tar.gz
    tar -xzvf LibreOffice_${LIBREOFFICE_VERSION}_Linux_x86-64_rpm.tar.gz
    cd LibreOffice*/RPMS
    sudo dnf install *.rpm -y
    export LIBRE_OFFICE_EXE=`find ${PATH//:/ } -maxdepth 1 -executable -name 'libreoffice*' | grep "libreoffice"`
    echo LIBRE_OFFICE_EXE=$LIBRE_OFFICE_EXE

    # Chrome + Selenium to get webpage
    cd /tmp
    download https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
    sudo dnf localinstall -y google-chrome-stable_current_x86_64.rpm
fi 
cd $SCRIPT_DIR

# Store the config in APEX
export TNS_ADMIN=$HOME/db
$HOME/db/sqlcl/bin/sql $DB_USER/$DB_PASSWORD@DB <<EOF
begin
  update APEX_APP.AI_AGENT_RAG_CONFIG set value='$TF_VAR_agent_endpoint_ocid' where key='agent_endpoint_ocid';
  update APEX_APP.AI_AGENT_RAG_CONFIG set value='$TF_VAR_region'              where key='region';
  update APEX_APP.AI_AGENT_RAG_CONFIG set value='$TF_VAR_compartment_ocid'    where key='compartment_ocid';
  update APEX_APP.AI_AGENT_RAG_CONFIG set value='$TF_VAR_genai_embed_model'   where key='genai_embed_model';
  commit;
end;
/
exit;
EOF

# Get COMPARTMENT_OCID
curl -s -H "Authorization: Bearer Oracle" -L http://169.254.169.254/opc/v2/instance/ > /tmp/instance.json
export TF_VAR_compartment_ocid=`cat /tmp/instance.json | jq -r .compartmentId`

# Create services
create_service () {
    APP_DIR=$1
    COMMAND=$2
    # Create an db service
    cat > /tmp/$COMMAND.service << EOT
[Unit]
Description=$COMMAND
After=network.target

[Service]
Type=simple
ExecStart=/home/opc/$APP_DIR/${COMMAND}.sh
TimeoutStartSec=0
User=opc

[Install]
WantedBy=default.target
EOT
    sudo cp /tmp/$COMMAND.service /etc/systemd/system
    sudo chmod 664 /etc/systemd/system/$COMMAND.service
    sudo systemctl daemon-reload
    sudo systemctl enable $COMMAND.service
    sudo systemctl restart $COMMAND.service
}

create_service app ingest
create_service app streamlit
create_service app tools

sudo firewall-cmd --zone=public --add-port=8081/tcp --permanent

