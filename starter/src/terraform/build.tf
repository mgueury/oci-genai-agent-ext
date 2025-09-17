locals {
  project_dir = (var.infra_as_code=="from_resource_manager")?".":"../.."
}

## BUILD_DEPLOY
resource "null_resource" "build_deploy" {
  provisioner "local-exec" {
    command = <<-EOT
        export BASTION_IP="${local.local_bastion_ip}"
        export CONTAINER_PREFIX="${local.local_container_prefix}"
        export DB_URL="${local.local_db_url}"
        export IDCS_URL="${local.local_idcs_url}"
        export JDBC_URL="${local.local_jdbc_url}"
        export OCIR_HOST="${local.local_ocir_host}"
        export ORDS_URL="${local.local_ords_url}"     
        cd ${local.project_dir}
        # pwd
        # ls -al target
        # cat target/terraform.tfstate
        # export
        export CALLED_BY_TERRAFORM="true"
        . ./starter.sh env
        # Run config command on the DB directly (ex RAC)

        # Build the DB tables (via Bastion)
        if [ -d src/db ]; then
            title "Deploy Bastion"
            $BIN_DIR/deploy_bastion.sh
            exit_on_error "Deploy Bastion"   
        fi  

        # Init target/compute
        if is_deploy_compute; then
            mkdir -p target/compute
            cp -r src/compute target/compute/.
        fi

        # Build all app* directories
        for APP_DIR in `app_dir_list`; do
            title "Build App $APP_DIR"
            src/$APP_DIR/build_app.sh
            exit_on_error "Build App $APP_DIR"
        done

        if [ -f src/ui/build_ui.sh ]; then
            title "Build UI"
            src/ui/build_ui.sh 
            exit_on_error "Build UI"
        fi

        # Deploy
        title "Deploy $TF_VAR_deploy_type"
        if is_deploy_compute; then
            $BIN_DIR/deploy_compute.sh
            exit_on_error "Deploy $TF_VAR_deploy_type"
        elif [ "$TF_VAR_deploy_type" == "kubernetes" ]; then
            $BIN_DIR/deploy_oke.sh
            exit_on_error "Deploy $TF_VAR_deploy_type"
        elif [ "$TF_VAR_deploy_type" == "container_instance" ]; then
            $BIN_DIR/deploy_ci.sh
            exit_on_error "Deploy $TF_VAR_deploy_type"
        fi
        ./starter.sh frm
        EOT
  }
  depends_on = [
    oci_apigateway_api.starter_api,
    oci_apigateway_gateway.starter_apigw,
    oci_artifacts_container_repository.starter_repo_fn,
    oci_core_instance.starter_bastion,
    oci_database_autonomous_database.starter_atp,
    oci_functions_application.starter_fn_application,
    oci_identity_policy.starter_fn_policy,
    oci_logging_log.export_starter_fn_application_invoke,
    oci_logging_log_group.starter_log_group,
    oci_objectstorage_bucket.starter_bucket, 
    oci_generative_ai_agent_agent_endpoint.starter_agent_endpoint   
  ]

  triggers = {
    always_run = "${timestamp()}"
  }      
}
# PART2
#
# In case like instance_pool, oke, function, container_instance, ...
# More terraform resources need to be created after build_deploy.
# Reread the env variables
data "external" "env_part2" {
  program = ["cat", "${local.project_dir}/target/resource_manager_variables.json"]
  depends_on = [
    null_resource.build_deploy
  ]
}

## AFTER_BUILD
# Last action at the end of the build
resource "null_resource" "after_build" {
  provisioner "local-exec" {
    command = <<-EOT
        export BASTION_IP="${local.local_bastion_ip}"
        export CONTAINER_PREFIX="${local.local_container_prefix}"
        export DB_URL="${local.local_db_url}"
        export IDCS_URL="${local.local_idcs_url}"
        export JDBC_URL="${local.local_jdbc_url}"
        export OCIR_HOST="${local.local_ocir_host}"
        export ORDS_URL="${local.local_ords_url}"     
        cd ${local.project_dir}    
        . ./starter.sh env    
        if [ "$TF_VAR_tls" != "" ]; then
            title "Certificate - Post Deploy"
            certificate_post_deploy 
        fi

        $BIN_DIR/add_api_portal.sh

        # Custom code after build
        if [ -f $PROJECT_DIR/src/after_build.sh ]; then
            $PROJECT_DIR/src/after_build.sh
        fi
        title "Done"
        $BIN_DIR/done.sh          
        EOT
  }
  depends_on = [
    oci_apigateway_deployment.starter_apigw_deployment,
    oci_functions_function.starter_fn_function,      
    null_resource.build_deploy
  ]

  triggers = {
    always_run = "${timestamp()}"
  }    
}

# BEFORE_DESTROY
resource "null_resource" "before_destroy" {
  provisioner "local-exec" {
      when = destroy
      command = <<-EOT
        if [ ! -f starter.sh ]; then 
          cd ../..
        fi
        ./starter.sh destroy --called_by_resource_manager
        EOT
  }

  depends_on = [  
    null_resource.after_build
  ]
}