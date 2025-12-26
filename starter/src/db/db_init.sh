#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Install SQLCL (Java program)
wget -nv https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip
rm -Rf sqlcl
unzip sqlcl-latest.zip
sudo dnf install -y java-17 

# Install SQL*Plus
if [[ `arch` == "aarch64" ]]; then
  sudo dnf install -y oracle-release-el8 
  sudo dnf install -y oracle-instantclient19.19-basic oracle-instantclient19.19-sqlplus oracle-instantclient19.19-tools
else
  export INSTANT_VERSION=23.26.0.0.0-1
  wget -nv https://download.oracle.com/otn_software/linux/instantclient/2326000/oracle-instantclient-basic-${INSTANT_VERSION}.el8.x86_64.rpm
  wget -nv https://download.oracle.com/otn_software/linux/instantclient/2326000/oracle-instantclient-sqlplus-${INSTANT_VERSION}.el8.x86_64.rpm
  wget -nv https://download.oracle.com/otn_software/linux/instantclient/2326000/oracle-instantclient-tools-${INSTANT_VERSION}.el8.x86_64.rpm
  sudo dnf install -y oracle-instantclient-basic-${INSTANT_VERSION}.el8.x86_64.rpm oracle-instantclient-sqlplus-${INSTANT_VERSION}.el8.x86_64.rpm oracle-instantclient-tools-${INSTANT_VERSION}.el8.x86_64.rpm
  mv *.rpm /tmp
fi

# Create the script to install the APEX Application
cat > import_application.sql << EOF 
create user if not exists apex_app identified by "$DB_PASSWORD" default tablespace USERS quota unlimited on USERS temporary tablespace TEMP; 
/
grant connect, resource, create role, unlimited tablespace to apex_app;
/
EXEC DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL('APEX_APP');
grant execute on DBMS_CLOUD to APEX_APP;
grant execute on DBMS_CLOUD_AI to APEX_APP;
grant execute on CTX_DDL to APEX_APP;
grant execute on DBMS_SCHEDULER to APEX_APP;
grant xs_session_admin, create session to APEX_APP;
grant execute on DBMS_XS_SESSIONS to apex_app;
BEGIN
    -- Grant system privileges
    SYS.XS_ADMIN_CLOUD_UTIL.GRANT_SYSTEM_PRIVILEGE('ADMIN_ANY_SEC_POLICY','APEX_APP',SYS.XS_ADMIN_UTIL.PTYPE_DB,NULL);
END;
/
grant create any job to APEX_APP;
/
begin
    apex_instance_admin.add_workspace(
     p_workspace_id   => null,
     p_workspace      => 'APEX_APP',
     p_primary_schema => 'APEX_APP');
end;
/
begin
    apex_application_install.set_workspace('APEX_APP');
    apex_application_install.set_application_id(1001);
    apex_application_install.generate_offset();
    apex_application_install.set_schema('APEX_APP');
    apex_application_install.set_auto_install_sup_obj( true );
end;
/
declare
    l_workspace_id number;
    l_group_id     number;
begin
    apex_application_install.set_workspace('APEX_APP');
    l_workspace_id := apex_util.find_security_group_id('APEX_APP');
    apex_util.set_security_group_id(l_workspace_id);
    -- l_group_id := apex_util.get_group_id('APEX_APP');
    apex_util.create_user(p_user_name           => 'APEX_APP',
                        p_email_address         => 'spam@oracle.com',
                        p_web_password          => '$DB_PASSWORD',
                        p_default_schema        => 'APEX_APP',
                        p_change_password_on_first_use => 'N',
                        p_developer_privs       => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
                        p_allow_app_building_yn => 'Y',
                        p_allow_sql_workshop_yn => 'Y',
                        p_allow_websheet_dev_yn => 'Y',
                        p_allow_team_development_yn => 'Y');                          
    COMMIT;                      
end;
/
@ai_agent_rag.sql
/
begin
    apex_application_install.set_application_id(1002);
end;
/
@ai_agent_rag_admin.sql
/
begin
    apex_application_install.set_application_id(1003);
end;
/
@ai_agent_eval.sql
begin
    apex_application_install.set_application_id(1004);
end;
/
@ai_support.sql
quit
EOF

# Run sqlcl
# Install the tables
cat > tnsnames.ora <<EOT
DB  = $DB_URL
EOT

export TNS_ADMIN=$HOME/db
sqlcl/bin/sql ADMIN/$DB_PASSWORD@DB @import_application.sql

# Install DocChunks 
sqlcl/bin/sql ADMIN/$DB_PASSWORD@DB @doc_chunck.sql

# Install SR for SQL agent
cat > support_table.sql << EOF 
CREATE TABLE SUPPORT_OWNER (
    id NUMBER PRIMARY KEY,
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE NOT NULL,
    phone VARCHAR2(20)
);

CREATE TABLE SUPPORT_SR (
    id NUMBER PRIMARY KEY,
    customer_name VARCHAR2(200) NOT NULL,
    subject VARCHAR2(200) NOT NULL,
    question CLOB NOT NULL,
    answer CLOB NOT NULL,
    create_date DATE DEFAULT SYSTIMESTAMP NOT NULL,
    last_update_date DATE DEFAULT SYSTIMESTAMP NOT NULL,
    owner_id NUMBER,
    embedding VECTOR,
    internal NUMBER
    FOREIGN KEY (owner_id) REFERENCES SUPPORT_OWNER(id)
);
exit;
EOF

sqlcl/bin/sql APEX_APP/$DB_PASSWORD@DB @support_table.sql

# Import the tables
/usr/lib/oracle/23/client64/bin/sqlldr APEX_APP/$DB_PASSWORD@DB CONTROL=support_owner.ctl
/usr/lib/oracle/23/client64/bin/sqlldr APEX_APP/$DB_PASSWORD@DB CONTROL=support_sr.ctl
/usr/lib/oracle/23/client64/bin/sqlldr APEX_APP/$DB_PASSWORD@DB CONTROL=ai_eval_question_answer.ctl

# Update the Indexes
cat > support_index.sql << EOF 
begin
  update SUPPORT_SR set EMBEDDING=ai_plsql.genai_embed( question || chr(13) || answer  );
  commit;
end;
/
-- CREATE INDEX SUPPORT_SR_QUESTION_IDX ON SUPPORT_SR(question) INDEXTYPE IS CTXSYS.CONTEXT;    
-- CREATE INDEX SUPPORT_SR_ANSWER_IDX ON SUPPORT_SR(answer) INDEXTYPE IS CTXSYS.CONTEXT;   
-- EXEC CTX_DDL.SYNC_INDEX('SUPPORT_SR_QUESTION_IDX');
-- EXEC CTX_DDL.SYNC_INDEX('SUPPORT_SR_ANSWER_IDX');

CREATE VECTOR INDEX SUPPORT_SR_HNSW_IDX ON APEX_APP.SUPPORT_SR(embedding) ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95;


exec sys.xs_principal.create_role(name => 'employee_role', enabled => true);
exec sys.xs_principal.create_role(name => 'customer_role', enabled => true);

create role ras_role;
grant select on apex_app.support_sr to ras_role;
grant execute on apex_app.ai_plsql to ras_role;
grant ras_role to employee_role;
grant ras_role to customer_role;

exec sys.xs_principal.create_user(name => 'employee', schema => 'APEX_APP');
exec sys.xs_principal.set_password('employee', 'Not__Used1234');
exec sys.xs_principal.create_user(name => 'customer', schema => 'APEX_APP');
exec sys.xs_principal.set_password('customer', 'Not__Used1234');

exec  sys.xs_principal.grant_roles('employee', 'employee_role');
exec  sys.xs_principal.grant_roles('customer', 'customer_role');

begin
    sys.xs_security_class.create_security_class(
    name => 'SUPPORT_SR_SEC_CLASS',
    description => 'Security Class',
    parent_list => XS$NAME_LIST('SYS.DML'),
    priv_list => xs$privilege_list(xs$privilege('internal_sr')));
end;
/

-- Creation of the ACL & mapping of the previously created roles : 
declare  
  aces xs$ace_list := xs$ace_list();  
begin 
  aces.extend(1);
  aces(1) := xs$ace_type(privilege_list => xs$name_list
                            ('select'),
                             principal_name => 'customer_role');
  sys.xs_acl.create_acl(name => 'customer_acl',
                    ace_list  => aces,
                    sec_class => 'SUPPORT_SR_SEC_CLASS');

  aces(1) := xs$ace_type(privilege_list => xs$name_list
                            ('select','internal_sr'),
                             principal_name => 'employee_role');
  sys.xs_acl.create_acl(name => 'employee_acl',
                    ace_list  => aces,
                    sec_class => 'SUPPORT_SR_SEC_CLASS');

  aces(1) := xs$ace_type(privilege_list => xs$name_list
                            ('select','insert','update','delete','index'),
                             principal_name => 'APEX_APP',
                             principal_type=>XS_ACL.PTYPE_DB);
  sys.xs_acl.create_acl(name => 'apex_app_acl',
                    ace_list  => aces,
                    sec_class => 'SUPPORT_SR_SEC_CLASS');                    
end;
/

-- Creation of a policy 
declare
  realms   xs$realm_constraint_list := xs$realm_constraint_list();      
  cols     xs$column_constraint_list := xs$column_constraint_list();
begin  
  realms.extend(3);
  realms(1) := xs$realm_constraint_type(
    realm=> '1=1',acl_list => xs$name_list('employee_acl'));
  
  realms(2) := xs$realm_constraint_type(
    realm=> 'internal=0',acl_list => xs$name_list('customer_acl'));

  realms(3) := xs$realm_constraint_type(
    realm=> '1=1',acl_list => xs$name_list('apex_app_acl'));    

  sys.xs_data_security.create_policy(
    name                   => 'support_sr_policy',
    realm_constraint_list  => realms);
end;
/

-- Apply the policy to the table
begin
    XS_DATA_SECURITY.apply_object_policy(
        schema=>'apex_app', 
        object=>'support_sr',
        policy=>'support_sr_policy',
        statement_types=>'SELECT');
end;    
/  

begin
  if (sys.xs_diag.validate_workspace()) then
    dbms_output.put_line('All configurations are correct.');
  else
    dbms_output.put_line('Some configurations are incorrect.');
  end if;
end;
/
select * from xs$validation_table order by 1, 2, 3, 4;
/
exit;
EOF

sqlcl/bin/sql APEX_APP/$DB_PASSWORD@DB @support_index.sql


# ORCL_DB_SSE (Micronaut)
cat > orcl_db_sse.sql << EOF 
CREATE TABLE SSE_EVENTS (
  ID NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY, 
  SSE_ID VARCHAR2(200),
  THREAD_ID VARCHAR2(200),
  EVENT_ORDER NUMBER,
  EVENT_NAME VARCHAR2(200),
  TYPE VARCHAR2(200),
  NAME VARCHAR2(1024),
  FINISH_REASON VARCHAR2(200),
  CREATEDATE TIMESTAMP,
  DATA_CONTENT CLOB,
  HTML_CONTENT CLOB,
  FULL_DATA CLOB
);
CREATE INDEX IDX_SSE_EVENTS_THREAD ON SSE_EVENTS(THREAD_ID);

CREATE TABLE SSE_DATA (
  ID NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
  CREATEDATE TIMESTAMP
  THREAD_ID VARCHAR2(200),
  EVENT_ID VARCHAR2(200),
  EVENT_NAME VARCHAR2(200),
  EVENT_DATA CLOB,
);

CREATE INDEX IDX_SSE_DATA_THREAD ON SSE_DATA(THREAD_ID);
EOF

sqlcl/bin/sql APEX_APP/$DB_PASSWORD@DB @orcl_db_sse.sql